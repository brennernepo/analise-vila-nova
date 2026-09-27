"""Simula o restante da Série B 2026 e calcula as chances de cada clube.

Modelo: os gols de cada jogo seguem uma distribuição de Poisson cuja média depende da
força de ataque do time, da força de defesa do adversário e da vantagem de jogar em
casa (modelo de Maher). As forças são estimadas por máxima verossimilhança nos jogos
já disputados, com encolhimento (ridge) para que campanhas curtas não pareçam mais
fortes ou mais fracas do que são. A intensidade do encolhimento é escolhida por
validação temporal deslizante (o modelo treina até cada corte e prevê os 20 jogos
seguintes). Como a validação quase não distingue os valores testados, o script também
roda variantes, e a faixa entre elas é a medida honesta da incerteza do modelo.

Com o modelo ajustado, o script simula milhares de vezes os jogos restantes de todos
os clubes e aplica o regulamento da CBF (REC Série B 2026):
- Art. 12: desempate por vitórias, saldo, gols pró e confronto direto (só quando
  exatamente dois clubes empatam em pontos, § 2º; placar somado dos dois jogos);
  cartões viram sorteio;
- Art. 13: mata-mata 3º x 6º e 4º x 5º em ida e volta, volta na casa do mais bem
  colocado; decide a soma de pontos, depois o saldo e, por fim, a posição;
- Art. 5: sobem os 2 primeiros e os 2 vencedores do mata-mata; caem os 4 últimos.

Saídas: simulacao_2026.js (carregado pelo painel) e serie_b_2026_probabilidades.csv.

Uso:
    python simulacao.py            (lê serie_b_2026_jogos.csv, gerado por coleta_detalhada.py)
"""

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson


ROOT = Path(__file__).resolve().parent
ARQUIVO_JOGOS = ROOT / "serie_b_2026_jogos.csv"
ARQUIVO_JS = ROOT / "simulacao_2026.js"
ARQUIVO_CSV = ROOT / "serie_b_2026_probabilidades.csv"

TIME = "Vila Nova"
SIMULACOES = 100_000
SIMULACOES_SENSIBILIDADE = 30_000
MAX_GOLS = 10                       # placares de 0 a 10 gols por time
GRADE_LAMBDA = [0.5, 1, 2, 3, 5, 8, 12, 20, 35, 60]
LAMBDA_PADRAO = 5.0                 # usado quando ainda há poucos jogos para validar
HORIZONTE_VALIDACAO = 20            # jogos previstos em cada corte da validação
MEIA_VIDA_DIAS = 60                 # variante de sensibilidade com peso temporal
ZONA_DIRETA, ZONA_PLAYOFF, ZONA_REBAIXAMENTO = 2, 6, 4
MIN_CASOS_CURVA = 300               # pontuações com menos simulações ficam fora das curvas
N_CLUBES = 20                       # Série B: 20 clubes, turno e returno (380 jogos)
MANDO_HISTORICO = np.log(1.3)       # vantagem de mando típica, usada com base curta
PESO_MANDO_BASE_CURTA = 10.0


# =========================================================
# 1. DADOS
# =========================================================

def carregar_jogos():
    jogos = pd.read_csv(ARQUIVO_JOGOS, encoding="utf-8-sig")
    jogos["data"] = pd.to_datetime(jogos["data"], errors="coerce")
    times = sorted(set(jogos["mandante"]) | set(jogos["visitante"]))
    indice = {nome: i for i, nome in enumerate(times)}

    finalizados = jogos[jogos["status"] == "finished"]
    sem_placar = finalizados[finalizados[["gols_mandante", "gols_visitante"]].isna().any(axis=1)]
    sem_data = finalizados[finalizados["data"].isna()]
    if len(sem_placar) or len(sem_data):
        raise SystemExit(f"Jogos encerrados incompletos: {len(sem_placar)} sem placar e {len(sem_data)} sem data "
                         f"(ids: {', '.join(map(str, pd.concat([sem_placar, sem_data])['id_jogo'].unique()[:10]))})")
    if finalizados.empty:
        raise SystemExit("Nenhum jogo encerrado na base: não há como estimar a força dos clubes.")
    for status in ("cancelled", "abandoned"):
        casos = jogos[jogos["status"] == status]
        if len(casos):
            print(f"Aviso: {len(casos)} jogo(s) com status '{status}' serão simulados como pendentes.")

    encerrados = finalizados.copy()
    encerrados = encerrados.sort_values(["data", "id_jogo"]).reset_index(drop=True)
    encerrados["casa"] = encerrados["mandante"].map(indice)
    encerrados["fora"] = encerrados["visitante"].map(indice)
    encerrados["gm"] = encerrados["gols_mandante"].astype(int)
    encerrados["gv"] = encerrados["gols_visitante"].astype(int)

    # Turno e returno: cada clube recebe todos os outros uma vez. O que ainda não foi
    # disputado é o que resta, mesmo que a fonte não traga jogos futuros, adiados ou em andamento.
    disputados = set(zip(encerrados["casa"], encerrados["fora"]))
    restantes = np.array([(c, f) for c in range(len(times)) for f in range(len(times))
                          if c != f and (c, f) not in disputados], dtype=int).reshape(-1, 2)
    return jogos, times, encerrados, restantes


def classificacao(n_times, encerrados):
    tabela = {chave: np.zeros(n_times, int) for chave in ("J", "V", "E", "D", "GP", "GC")}
    for casa, fora, gm, gv in zip(encerrados["casa"], encerrados["fora"], encerrados["gm"], encerrados["gv"]):
        tabela["J"][casa] += 1
        tabela["J"][fora] += 1
        tabela["GP"][casa] += gm
        tabela["GC"][casa] += gv
        tabela["GP"][fora] += gv
        tabela["GC"][fora] += gm
        if gm > gv:
            tabela["V"][casa] += 1
            tabela["D"][fora] += 1
        elif gm < gv:
            tabela["V"][fora] += 1
            tabela["D"][casa] += 1
        else:
            tabela["E"][casa] += 1
            tabela["E"][fora] += 1
    tabela["P"] = 3 * tabela["V"] + tabela["E"]
    return tabela


def conferir_base(jogos, times, encerrados, restantes):
    """Interrompe a execução se a base não for a de um turno e returno de 20 clubes."""
    n = len(times)
    esperado = N_CLUBES * (N_CLUBES - 1)
    problemas = []
    if n != N_CLUBES:
        contagem = pd.concat([jogos["mandante"], jogos["visitante"]]).value_counts()
        raros = ", ".join(f"{nome} ({qtd})" for nome, qtd in contagem.sort_values().head(n - N_CLUBES + 3).items())
        problemas.append(f"{n} clubes em vez de {N_CLUBES}; nomes menos frequentes: {raros}")
    duplicados = encerrados.duplicated(subset=["casa", "fora"]).sum()
    if duplicados:
        problemas.append(f"{duplicados} confrontos disputados em duplicidade")
    # Com a tabela completa na fonte (ESPN), cada clube tem 19 jogos como mandante e 19 como visitante.
    if len(jogos) == esperado:
        for coluna in ("mandante", "visitante"):
            fora_do_padrao = jogos[coluna].value_counts().loc[lambda qtd: qtd != N_CLUBES - 1]
            if len(fora_do_padrao):
                problemas.append(f"clubes sem 19 jogos como {coluna}: {dict(fora_do_padrao)}")
        pendentes = jogos[jogos["status"] != "finished"]
        indice = {nome: i for i, nome in enumerate(times)}
        pares_pendentes = set(zip(pendentes["mandante"].map(indice), pendentes["visitante"].map(indice)))
        if pares_pendentes != set(map(tuple, restantes)):
            problemas.append("os jogos restantes não batem com os jogos não encerrados da base")
    elif (jogos["status"] != "finished").any():
        problemas.append(f"{len(jogos)} jogos na base, com jogos futuros, em vez de {esperado}")
    else:
        # Base só com jogos encerrados (Football Soccer API): sem o calendário, um jogo disputado
        # que falte na base não tem como ser detectado e seria simulado como pendente.
        por_clube = pd.concat([jogos["mandante"], jogos["visitante"]]).value_counts()
        print(f"Aviso: base só com jogos encerrados ({len(jogos)} de {esperado}); os {esperado - len(jogos)} "
              f"confrontos restantes serão simulados. Confira se nenhum jogo disputado ficou de fora: "
              f"de {por_clube.min()} a {por_clube.max()} jogos por clube.")
    if problemas:
        raise SystemExit("Base da liga inconsistente: " + "; ".join(problemas))
    return {"total_jogos": esperado, "jogos_por_clube": 2 * (N_CLUBES - 1),
            "jogos_na_base": int(len(jogos)), "calendario_conferido": bool(len(jogos) == esperado)}


# =========================================================
# 2. MODELO DE GOLS (POISSON COM ENCOLHIMENTO)
# =========================================================

def ajustar(jogos, n_times, lam, pesos=None, mando_prior=None):
    """Parâmetros: [média, mando, ataque (n), defesa (n)], em escala log.
    mando_prior=(valor, peso) encolhe a vantagem de mando para um valor típico (base curta)."""
    casa, fora = jogos["casa"].to_numpy(), jogos["fora"].to_numpy()
    gm, gv = jogos["gm"].to_numpy(float), jogos["gv"].to_numpy(float)
    w = np.ones(len(jogos)) if pesos is None else pesos

    def custo(theta):
        media, mando = theta[0], theta[1]
        ataque, defesa = theta[2:2 + n_times], theta[2 + n_times:]
        eta_casa = media + mando + ataque[casa] - defesa[fora]
        eta_fora = media + ataque[fora] - defesa[casa]
        lam_casa, lam_fora = np.exp(eta_casa), np.exp(eta_fora)
        valor = -(w * (gm * eta_casa - lam_casa + gv * eta_fora - lam_fora)).sum() \
            + 0.5 * lam * (ataque @ ataque + defesa @ defesa)
        d_casa, d_fora = w * (gm - lam_casa), w * (gv - lam_fora)
        grad = np.zeros_like(theta)
        grad[0] = -(d_casa.sum() + d_fora.sum())
        grad[1] = -d_casa.sum()
        grad[2:2 + n_times] = -(np.bincount(casa, d_casa, n_times) + np.bincount(fora, d_fora, n_times)) + lam * ataque
        grad[2 + n_times:] = np.bincount(fora, d_casa, n_times) + np.bincount(casa, d_fora, n_times) + lam * defesa
        if mando_prior is not None:
            alvo, peso = mando_prior
            valor += 0.5 * peso * (mando - alvo) ** 2
            grad[1] += peso * (mando - alvo)
        return valor, grad

    inicio = np.zeros(2 + 2 * n_times)
    inicio[0] = np.log(max((gm.sum() + gv.sum()) / (2 * len(jogos)), 0.1))
    resultado = minimize(custo, inicio, jac=True, method="L-BFGS-B", options={"maxiter": 5000})
    if not np.all(np.isfinite(resultado.x)) or not np.isfinite(resultado.fun):
        raise SystemExit(f"O ajuste do modelo não convergiu: {resultado.message}")
    return resultado.x


def medias(theta, n_times, casa, fora):
    media, mando = theta[0], theta[1]
    ataque, defesa = theta[2:2 + n_times], theta[2 + n_times:]
    return (np.exp(media + mando + ataque[casa] - defesa[fora]),
            np.exp(media + ataque[fora] - defesa[casa]))


def matriz_placares(lam_casa, lam_fora):
    gols = np.arange(MAX_GOLS + 1)
    matriz = poisson.pmf(gols[None, :, None], lam_casa[:, None, None]) * poisson.pmf(gols[None, None, :], lam_fora[:, None, None])
    return matriz / matriz.sum(axis=(1, 2), keepdims=True)


def probabilidades_resultado(matriz):
    vitoria_casa = np.tril(np.ones((MAX_GOLS + 1, MAX_GOLS + 1), bool), -1)
    p_casa = matriz[:, vitoria_casa].sum(1)
    p_empate = np.trace(matriz, axis1=1, axis2=2)
    return np.stack([p_casa, p_empate, 1 - p_casa - p_empate], 1)


def escolher_lambda(encerrados, n_times):
    """Validação temporal: treina até cada corte e mede o acerto (log-verossimilhança
    de vitória/empate/derrota) nos jogos seguintes."""
    n = len(encerrados)
    cortes = list(range(max(100, n // 2), n - HORIZONTE_VALIDACAO + 1, HORIZONTE_VALIDACAO))
    if len(cortes) < 3:
        return LAMBDA_PADRAO, {}
    placar = {}
    for lam in GRADE_LAMBDA:
        logs = []
        for corte in cortes:
            treino = encerrados.iloc[:corte]
            teste = encerrados.iloc[corte:corte + HORIZONTE_VALIDACAO]
            theta = ajustar(treino, n_times, lam)
            prob = probabilidades_resultado(matriz_placares(*medias(theta, n_times, teste["casa"].to_numpy(), teste["fora"].to_numpy())))
            real = np.where(teste["gm"] > teste["gv"], 0, np.where(teste["gm"] == teste["gv"], 1, 2))
            logs.extend(np.log(prob[np.arange(len(teste)), real]))
        placar[lam] = float(np.mean(logs))
    return max(placar, key=placar.get), placar


# =========================================================
# 3. SIMULAÇÃO DA TEMPORADA E DO MATA-MATA
# =========================================================

def sortear_placar(acumulada, rng, n):
    """Sorteia n placares a partir da distribuição acumulada de um jogo."""
    indices = np.searchsorted(acumulada, rng.random(n), side="right")
    return indices // (MAX_GOLS + 1), indices % (MAX_GOLS + 1)


def simular(theta, n_times, tabela, encerrados, restantes, rng, n):
    pontos = np.tile(tabela["P"], (n, 1))
    vitorias = np.tile(tabela["V"], (n, 1))
    saldo = np.tile(tabela["GP"] - tabela["GC"], (n, 1))
    gols_pro = np.tile(tabela["GP"], (n, 1))
    placares = np.zeros((n, len(restantes), 2), np.int8)

    if len(restantes):
        casa, fora = restantes[:, 0], restantes[:, 1]
        acumulada = np.cumsum(matriz_placares(*medias(theta, n_times, casa, fora)).reshape(len(restantes), -1), 1)
        acumulada[:, -1] = 1.0
        for j, (c, f) in enumerate(restantes):
            x, y = sortear_placar(acumulada[j], rng, n)
            placares[:, j, 0], placares[:, j, 1] = x, y
            pontos[:, c] += 3 * (x > y) + (x == y)
            pontos[:, f] += 3 * (y > x) + (x == y)
            vitorias[:, c] += x > y
            vitorias[:, f] += y > x
            saldo[:, c] += x - y
            saldo[:, f] += y - x
            gols_pro[:, c] += x
            gols_pro[:, f] += y

    # Art. 12: pontos, vitórias, saldo e gols pró; depois, confronto direto (só entre dois
    # clubes, placar somado dos dois jogos) e, por fim, sorteio no lugar dos cartões.
    chave = (pontos.astype(np.int64) * 10**9 + vitorias * 10**6 + (saldo + 500) * 10**3 + gols_pro).astype(np.float64)
    ordenada = np.sort(chave, axis=1)
    linhas_empate = np.where((ordenada[:, 1:] == ordenada[:, :-1]).any(1))[0]
    if len(linhas_empate):
        gols_entre = np.zeros((n_times, n_times), int)      # gols de i contra j nos jogos disputados
        for c, f, x, y in zip(encerrados["casa"], encerrados["fora"], encerrados["gm"], encerrados["gv"]):
            gols_entre[c, f] += x
            gols_entre[f, c] += y
        jogos_do_par = {}
        for j, (c, f) in enumerate(restantes):
            jogos_do_par.setdefault(frozenset((c, f)), []).append(j)
        for s in linhas_empate:
            valores, contagem = np.unique(chave[s], return_counts=True)
            for valor in valores[contagem == 2]:
                a, b = np.where(chave[s] == valor)[0]
                if (pontos[s] == pontos[s, a]).sum() != 2:
                    continue  # Art. 12, § 2º: com mais de 2 clubes empatados em pontos, não há confronto direto
                gols_a, gols_b = gols_entre[a, b], gols_entre[b, a]
                for j in jogos_do_par.get(frozenset((a, b)), []):
                    x, y = placares[s, j]
                    if restantes[j, 0] == a:
                        gols_a, gols_b = gols_a + x, gols_b + y
                    else:
                        gols_a, gols_b = gols_a + y, gols_b + x
                if gols_a != gols_b:
                    chave[s, a if gols_a > gols_b else b] += 0.5
    chave += rng.random((n, n_times)) * 0.1
    ordem = np.argsort(-chave, axis=1)
    posicao = np.empty_like(ordem)
    np.put_along_axis(posicao, ordem, np.arange(n_times)[None, :].repeat(n, 0), 1)

    # Art. 13: 3º x 6º e 4º x 5º. Ida na casa do pior colocado, volta na do melhor. Pontos
    # nos dois jogos, depois saldo; persistindo o empate, avança o mais bem colocado — o
    # que equivale a decidir pelo placar agregado com vantagem do mais bem colocado.
    todos_casa = np.repeat(np.arange(n_times), n_times)
    todos_fora = np.tile(np.arange(n_times), n_times)
    confrontos = np.cumsum(matriz_placares(*medias(theta, n_times, todos_casa, todos_fora)).reshape(n_times, n_times, -1), 2)
    confrontos[:, :, -1] = 1.0

    def jogo(mandante, visitante):
        indices = (rng.random(n)[:, None] >= confrontos[mandante, visitante]).sum(1)
        return indices // (MAX_GOLS + 1), indices % (MAX_GOLS + 1)

    acesso = np.zeros((n, n_times), bool)
    acesso_playoff = np.zeros((n, n_times), bool)
    linhas = np.arange(n)
    acesso[linhas, ordem[:, 0]] = True
    acesso[linhas, ordem[:, 1]] = True
    for melhor_pos, pior_pos in ((2, 5), (3, 4)):
        melhor, pior = ordem[:, melhor_pos], ordem[:, pior_pos]
        ida_pior, ida_melhor = jogo(pior, melhor)
        volta_melhor, volta_pior = jogo(melhor, pior)
        classificado = np.where(ida_pior + volta_pior > ida_melhor + volta_melhor, pior, melhor)
        acesso[linhas, classificado] = True
        acesso_playoff[linhas, classificado] = True
    return pontos, posicao, acesso, acesso_playoff


def conferir_simulacao(posicao, acesso, n_times):
    somas = {
        "acesso": float(acesso.sum(1).mean()),
        "acesso_direto": float((posicao < ZONA_DIRETA).sum(1).mean()),
        "rebaixamento": float((posicao >= n_times - ZONA_REBAIXAMENTO).sum(1).mean()),
    }
    esperado = {"acesso": 4, "acesso_direto": ZONA_DIRETA, "rebaixamento": ZONA_REBAIXAMENTO}
    if any(abs(somas[k] - esperado[k]) > 1e-9 for k in somas):
        raise SystemExit(f"Simulação inconsistente: somas por temporada {somas}, esperado {esperado}")
    return somas


# =========================================================
# 4. RESUMO E EXPORTAÇÃO
# =========================================================

def quantis(valores):
    return {"p10": int(np.percentile(valores, 10)), "mediana": int(np.percentile(valores, 50)), "p90": int(np.percentile(valores, 90))}


def curva(pontos_finais, evento):
    """P(evento | pontos finais), só para pontuações com simulações suficientes."""
    resultado = {}
    for total in np.unique(pontos_finais):
        casos = pontos_finais == total
        if casos.sum() >= MIN_CASOS_CURVA:
            resultado[str(int(total))] = round(float(evento[casos].mean()), 4)
    return resultado


def main():
    jogos, times, encerrados, restantes = carregar_jogos()
    n_times = len(times)
    checagens = conferir_base(jogos, times, encerrados, restantes)
    tabela = classificacao(n_times, encerrados)
    print(f"Clubes: {n_times} | jogos disputados: {len(encerrados)} | restantes: {len(restantes)}")

    lam, validacao = escolher_lambda(encerrados, n_times)
    base_curta = not validacao
    mando_prior = (MANDO_HISTORICO, PESO_MANDO_BASE_CURTA) if base_curta else None
    if base_curta:
        print("Aviso: poucos jogos disputados; chances preliminares, com mando encolhido para o valor típico.")
    theta = ajustar(encerrados, n_times, lam, mando_prior=mando_prior)
    print(f"Encolhimento escolhido: {lam} | vantagem de mando: x{np.exp(theta[1]):.2f} nos gols")

    recorte = encerrados["data"].max()
    semente = int(recorte.strftime("%Y%m%d"))
    rng = np.random.default_rng(semente)
    pontos, posicao, acesso, acesso_playoff = simular(theta, n_times, tabela, encerrados, restantes, rng, SIMULACOES)
    checagens.update({f"soma_{k}": v for k, v in conferir_simulacao(posicao, acesso, n_times).items()})

    vn = times.index(TIME)
    sensibilidade = [{"variante": f"principal (encolhimento {lam:g})", "acesso": round(float(acesso[:, vn].mean()), 4),
                      "acesso_direto": round(float((posicao[:, vn] < ZONA_DIRETA).mean()), 4)}]
    dias = (recorte - encerrados["data"]).dt.days.to_numpy()
    variantes = [
        ("encolhimento fraco (1)", {"lam": 1.0}),
        ("encolhimento forte (30)", {"lam": 30.0}),
        (f"peso maior para jogos recentes (meia-vida de {MEIA_VIDA_DIAS} dias)", {"lam": lam, "pesos": 0.5 ** (dias / MEIA_VIDA_DIAS)}),
    ]
    for nome, parametros in variantes:
        theta_v = ajustar(encerrados, n_times, parametros["lam"], parametros.get("pesos"), mando_prior)
        _, posicao_v, acesso_v, _ = simular(theta_v, n_times, tabela, encerrados, restantes,
                                            np.random.default_rng(semente + len(sensibilidade)), SIMULACOES_SENSIBILIDADE)
        sensibilidade.append({"variante": nome, "acesso": round(float(acesso_v[:, vn].mean()), 4),
                              "acesso_direto": round(float((posicao_v[:, vn] < ZONA_DIRETA).mean()), 4)})
    faixa = [item["acesso"] for item in sensibilidade]

    ordem_atual = sorted(range(n_times), key=lambda i: (-tabela["P"][i], -tabela["V"][i], -(tabela["GP"][i] - tabela["GC"][i]), -tabela["GP"][i]))
    clubes = []
    for posicao_atual, i in enumerate(ordem_atual, start=1):
        clubes.append({
            "time": times[i],
            "posicao": posicao_atual,
            "pontos": int(tabela["P"][i]),
            "jogos": int(tabela["J"][i]),
            "vitorias": int(tabela["V"][i]),
            "saldo": int(tabela["GP"][i] - tabela["GC"][i]),
            "pontos_medios": round(float(pontos[:, i].mean()), 1),
            "titulo": round(float((posicao[:, i] == 0).mean()), 4),
            "acesso_direto": round(float((posicao[:, i] < ZONA_DIRETA).mean()), 4),
            "g6": round(float((posicao[:, i] < ZONA_PLAYOFF).mean()), 4),
            "acesso_playoff": round(float(acesso_playoff[:, i].mean()), 4),
            "acesso": round(float(acesso[:, i].mean()), 4),
            "rebaixamento": round(float((posicao[:, i] >= n_times - ZONA_REBAIXAMENTO).mean()), 4),
        })

    datas = {(j["mandante"], j["visitante"]): j["data"].date().isoformat()
             for _, j in jogos[jogos["status"] != "finished"].iterrows() if pd.notna(j["data"])}
    jogos_vn = []
    proximos = [(c, f) for c, f in restantes if vn in (c, f)]
    if proximos:
        casa, fora = np.array(proximos).T
        prob = probabilidades_resultado(matriz_placares(*medias(theta, n_times, casa, fora)))
        for (c, f), (p_casa, p_empate, p_fora) in zip(proximos, prob):
            em_casa = c == vn
            jogos_vn.append({
                "data": datas.get((times[c], times[f])),
                "adversario": times[f] if em_casa else times[c],
                "mando": "Casa" if em_casa else "Fora",
                "vitoria": round(float(p_casa if em_casa else p_fora), 4),
                "empate": round(float(p_empate), 4),
                "derrota": round(float(p_fora if em_casa else p_casa), 4),
            })
        jogos_vn.sort(key=lambda j: (j["data"] is None, j["data"] or ""))

    finais_vn = pontos[:, vn]
    faixa_vn = quantis(finais_vn)
    pontos_por_posicao = np.sort(pontos, axis=1)[:, ::-1]
    mandantes = encerrados["gm"] > encerrados["gv"]
    empates = encerrados["gm"] == encerrados["gv"]
    visitantes = encerrados["gm"] < encerrados["gv"]
    p_acesso = float(acesso[:, vn].mean())
    aprov_mandante = (3 * mandantes.sum() + empates.sum()) / (3 * len(encerrados))
    aprov_visitante = (3 * visitantes.sum() + empates.sum()) / (3 * len(encerrados))

    dados = {
        "gerado_em": date.today().isoformat(),
        "recorte": recorte.date().isoformat(),
        "simulacoes": SIMULACOES,
        "semente": semente,
        "base_curta": base_curta,
        "erro_mc_acesso": round(float(np.sqrt(p_acesso * (1 - p_acesso) / SIMULACOES)), 4),
        "jogos_disputados": int(len(encerrados)),
        "jogos_restantes": int(len(restantes)),
        "regulamento": "REC Série B 2026 da CBF, Arts. 5, 12 e 13",
        "desempate": ["pontos", "vitorias", "saldo", "gols_pro", "confronto_direto", "sorteio"],
        "modelo": {
            "descricao": "Poisson com forças de ataque e defesa por clube e vantagem de mando, estimadas com encolhimento",
            "encolhimento": lam,
            "vantagem_mando": round(float(np.exp(theta[1])), 3),
            "validacao": {str(k): round(v, 4) for k, v in validacao.items()},
        },
        "sensibilidade": sensibilidade,
        "faixa_acesso": {"min": min(faixa), "max": max(faixa)},
        "liga": {
            "aproveitamento_mandante": round(float(aprov_mandante), 4),
            "aproveitamento_visitante": round(float(aprov_visitante), 4),
            "diferenca_pp": round(float(100 * (aprov_mandante - aprov_visitante)), 1),
        },
        "cortes": {
            "segundo": quantis(pontos_por_posicao[:, ZONA_DIRETA - 1]),
            "sexto": quantis(pontos_por_posicao[:, ZONA_PLAYOFF - 1]),
            "primeiro_rebaixado": quantis(pontos_por_posicao[:, n_times - ZONA_REBAIXAMENTO]),
        },
        "time": TIME,
        "resumo": next(c for c in clubes if c["time"] == TIME),
        "pontos_finais": {**faixa_vn, "cobertura": round(float(((finais_vn >= faixa_vn["p10"]) & (finais_vn <= faixa_vn["p90"])).mean()), 4)},
        "pontos_dist": {str(int(k)): round(float(v), 5) for k, v in zip(*np.unique(finais_vn, return_counts=True)) for v in [v / SIMULACOES]},
        "curva_top2": curva(finais_vn, posicao[:, vn] < ZONA_DIRETA),
        "curva_g6": curva(finais_vn, posicao[:, vn] < ZONA_PLAYOFF),
        "posicoes": [round(float((posicao[:, vn] == p).mean()), 4) for p in range(n_times)],
        "proximos_jogos": jogos_vn,
        "clubes": clubes,
        "checagens": checagens,
    }

    resumo = dados["resumo"]
    print(f"Conferências: {checagens}")
    print(f"{TIME}: acesso {resumo['acesso']:.1%} | direto {resumo['acesso_direto']:.1%} | "
          f"G6 {resumo['g6']:.1%} | título {resumo['titulo']:.1%} | rebaixamento {resumo['rebaixamento']:.1%}")
    print("Sensibilidade do acesso: " + " | ".join(f"{s['variante']}: {s['acesso']:.1%}" for s in sensibilidade))

    conteudo = json.dumps(dados, ensure_ascii=False, indent=2)
    ARQUIVO_JS.write_text(
        "// Gerado por simulacao.py. Para atualizar, rode o script novamente em vez de editar este arquivo.\n"
        f"window.VILA_NOVA_SIMULACAO = {conteudo};\n",
        encoding="utf-8",
    )
    pd.DataFrame(clubes).to_csv(ARQUIVO_CSV, index=False, encoding="utf-8-sig")
    print(f"Arquivos gerados: {ARQUIVO_JS.name}, {ARQUIVO_CSV.name}")


if __name__ == "__main__":
    main()
