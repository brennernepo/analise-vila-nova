"""Coleta os jogos do Vila Nova na Série B 2026 e gera a base consolidada da dashboard.

Duas fontes, com o mesmo formato de saída:

- Football Soccer API (plano gratuito), usada quando a variável FSAPI_KEY está
  definida — a mesma fonte do projeto original;
- API pública da ESPN, sem chave, usada automaticamente quando FSAPI_KEY não existe.
"""

import os
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests


TEMPORADA = 2026
ARQUIVO = "vila_nova_serie_b_2026_todos_jogos.csv"
ARQUIVO_LIGA = "serie_b_2026_jogos.csv"

# Football Soccer API — https://footballsoccerapi.com
FSAPI_KEY = os.environ.get("FSAPI_KEY")
FSAPI_URL = "https://api.footballsoccerapi.com/v1"
SERIE_B_ID = "lg_1VQKEDM"
# Opcional: com o id do clube definido, o script pula a busca pelo nome.
VILA_NOVA_ID = os.environ.get("VILA_NOVA_ID")

# ESPN — endpoints públicos, sem chave
ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.2"
ESPN_VILA_NOVA_ID = "9973"

BRASILIA = timezone(timedelta(hours=-3))
PAUSA = 0.25

# Padroniza os nomes das duas fontes (a Football Soccer API não usa acentos).
NOMES = {
    "America Mineiro": "América Mineiro",
    "Athletic": "Athletic Club",
    "Atletico Goianiense": "Atlético Goianiense",
    "Avai": "Avaí",
    "Botafogo SP": "Botafogo-SP",
    "Ceara": "Ceará",
    "Criciuma": "Criciúma",
    "Cuiaba": "Cuiabá",
    "Fortaleza EC": "Fortaleza",
    "Goias": "Goiás",
    "Nautico": "Náutico",
    "Operario-PR": "Operário-PR",
    "Operário PR": "Operário-PR",
    "Sport Recife": "Sport",
}
# Correções de grafia dos estádios e cidades informados pela ESPN.
ESTADIOS = {
    "Alfredo Jaconi": "Estádio Alfredo Jaconi",
    "Estadio VGD": "Estádio Vitorino Gonçalves Dias",
    "Germano Krüger": "Estádio Germano Krüger",
    "Heriberto Hülse": "Estádio Heriberto Hülse",
    "Ilha do Retiro": "Estádio Ilha do Retiro",
    "Moisés Lucarelli": "Estádio Moisés Lucarelli",
}
CIDADES = {
    "Goiãnia": "Goiânia",
    "Maceio, Alagoas": "Maceió",
    "Ponte Preta": "Campinas",
    "Sao Joao del Rei": "São João del-Rei",
}


def normalizar(texto):
    """Remove acentos e caixa para comparar nomes."""
    base = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in base if not unicodedata.combining(c)).casefold().strip()


def numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def get_json(url, headers=None, params=None):
    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


# =========================================================
# 1A. FONTE: FOOTBALL SOCCER API (com chave)
# =========================================================

def fsapi_get(caminho, params=None):
    return get_json(f"{FSAPI_URL}{caminho}", headers={"X-API-Key": FSAPI_KEY}, params=params)


def fsapi_id_vila_nova():
    if VILA_NOVA_ID:
        return VILA_NOVA_ID

    clubes = fsapi_get("/teams", {"league_id": SERIE_B_ID, "limit": 1000}).get("data", [])
    for clube in clubes:
        if normalizar(clube.get("team_name")) == "vila nova":
            print("Vila Nova encontrado:", clube["team_id"])
            return clube["team_id"]

    raise RuntimeError(
        "Vila Nova não encontrado em /v1/teams. Defina VILA_NOVA_ID com o id do clube."
    )


def fsapi_stats(jogo, nome_time):
    for item in jogo.get("statistics", []):
        if item.get("team_name") == nome_time:
            return item.get("statistics", {})
    return {}


def coletar_fsapi():
    time_id = fsapi_id_vila_nova()

    params = {
        "league_id": SERIE_B_ID,
        "team_id": time_id,
        "season": TEMPORADA,
        "limit": 1000,
        "sort": "kickoff_utc",
    }
    basicos, cursor = [], None
    while True:
        if cursor:
            params["cursor"] = cursor
        resposta = fsapi_get("/matches", params)
        basicos.extend(resposta.get("data", []))
        cursor = resposta.get("meta", {}).get("next_cursor")
        if not cursor:
            break

    jogos = []
    for numero_jogo, basico in enumerate(basicos, start=1):
        print(
            f"[{numero_jogo}/{len(basicos)}] "
            f"{basico.get('home_team_name')} x {basico.get('away_team_name')}"
        )

        # Só jogos encerrados têm estatísticas: poupa a cota diária do plano gratuito.
        jogo = basico
        if basico.get("match_status") == "finished":
            try:
                jogo = fsapi_get(f"/matches/{basico['match_id']}").get("data") or basico
            except requests.RequestException as erro:
                print("   Detalhes indisponíveis:", erro)
            time.sleep(PAUSA)

        mandante = jogo.get("home_team_name")
        visitante = jogo.get("away_team_name")
        if jogo.get("home_team_id"):
            em_casa = jogo["home_team_id"] == time_id
        else:
            em_casa = normalizar(mandante) == "vila nova"

        jogos.append({
            "id_jogo": jogo["match_id"],
            "data": jogo.get("kickoff_date"),
            "status": jogo.get("match_status"),
            "em_casa": em_casa,
            "mandante": mandante,
            "visitante": visitante,
            "gols_mandante": jogo.get("home_goals"),
            "gols_visitante": jogo.get("away_goals"),
            "gols_1t_mandante": jogo.get("half_time_home_goals"),
            "gols_1t_visitante": jogo.get("half_time_away_goals"),
            "estadio": jogo.get("venue_name"),
            "cidade": jogo.get("city_name"),
            "stats_mandante": fsapi_stats(jogo, mandante),
            "stats_visitante": fsapi_stats(jogo, visitante),
        })

    return jogos


# =========================================================
# 1B. FONTE: ESPN (sem chave)
# =========================================================

# Nomes das estatísticas da ESPN no padrão da Football Soccer API.
ESPN_STATS = {
    "possession_pct": "possessionPct",
    "shots_total": "totalShots",
    "shots_on_target": "shotsOnTarget",
    "shots_blocked": "blockedShots",
    "corners": "wonCorners",
    "fouls": "foulsCommitted",
    "offsides": "offsides",
    "passes_total": "totalPasses",
    "passes_accurate": "accuratePasses",
    "yellow_cards": "yellowCards",
    "red_cards": "redCards",
    "saves": "saves",
}


def espn_status(tipo):
    nome = tipo.get("name", "")
    for trecho, status in (("POSTPONED", "postponed"), ("CANCEL", "cancelled"), ("ABANDON", "abandoned")):
        if trecho in nome:
            return status
    if tipo.get("completed"):
        return "finished"
    return "live" if tipo.get("state") == "in" else "scheduled"


def espn_placar(score):
    if isinstance(score, dict):
        score = score.get("displayValue")
    valor = numero(score)
    return None if valor is None else int(valor)


def espn_stats(time_boxscore):
    brutos = {
        item.get("name"): numero(item.get("displayValue"))
        for item in time_boxscore.get("statistics", [])
    }
    stats = {chave: brutos.get(nome) for chave, nome in ESPN_STATS.items()}

    # A ESPN não informa os chutes para fora: total = no alvo + para fora + bloqueados.
    if None not in (stats["shots_total"], stats["shots_on_target"], stats["shots_blocked"]):
        stats["shots_off_target"] = (
            stats["shots_total"] - stats["shots_on_target"] - stats["shots_blocked"]
        )
    return stats


def espn_detalhar(jogo, evento_id):
    resumo = get_json(f"{ESPN_URL}/summary", params={"event": evento_id})

    competidores = resumo["header"]["competitions"][0]["competitors"]
    for competidor in competidores:
        lado = "mandante" if competidor["homeAway"] == "home" else "visitante"
        gols = espn_placar(competidor.get("score"))
        parciais = [espn_placar(p.get("displayValue")) for p in competidor.get("linescores", [])]

        jogo[f"gols_{lado}"] = gols
        if parciais and None not in parciais and sum(parciais) == gols:
            jogo[f"gols_1t_{lado}"] = parciais[0]
        else:
            print("   Placar do intervalo indisponível ou inconsistente:", parciais)

    for time_boxscore in resumo.get("boxscore", {}).get("teams", []):
        lado = "mandante" if time_boxscore.get("homeAway") == "home" else "visitante"
        jogo[f"stats_{lado}"] = espn_stats(time_boxscore)

    estadio = resumo.get("gameInfo", {}).get("venue", {})
    jogo["estadio"] = estadio.get("fullName") or jogo["estadio"]
    jogo["cidade"] = estadio.get("address", {}).get("city") or jogo["cidade"]


def coletar_espn():
    eventos = {}
    # Sem "fixture", a agenda traz os jogos disputados; com ela, os próximos.
    for extra in ({}, {"fixture": "true"}):
        agenda = get_json(
            f"{ESPN_URL}/teams/{ESPN_VILA_NOVA_ID}/schedule",
            params={"season": TEMPORADA, **extra},
        )
        for evento in agenda.get("events", []):
            eventos[evento["id"]] = evento
    ordenados = sorted(eventos.values(), key=lambda evento: evento["date"])

    jogos = []
    for numero_jogo, evento in enumerate(ordenados, start=1):
        competicao = evento["competitions"][0]
        lados = {c["homeAway"]: c for c in competicao["competitors"]}
        casa, fora = lados["home"], lados["away"]
        status = espn_status(competicao.get("status", {}).get("type", {}))
        inicio = datetime.fromisoformat(evento["date"].replace("Z", "+00:00"))
        estadio = competicao.get("venue") or {}

        print(
            f"[{numero_jogo}/{len(ordenados)}] "
            f"{casa['team']['displayName']} x {fora['team']['displayName']} ({status})"
        )

        jogo = {
            "id_jogo": f"espn_{evento['id']}",
            "data": inicio.astimezone(BRASILIA).date().isoformat(),
            "status": status,
            "em_casa": casa["team"]["id"] == ESPN_VILA_NOVA_ID,
            "mandante": casa["team"]["displayName"],
            "visitante": fora["team"]["displayName"],
            "gols_mandante": espn_placar(casa.get("score")),
            "gols_visitante": espn_placar(fora.get("score")),
            "gols_1t_mandante": None,
            "gols_1t_visitante": None,
            "estadio": estadio.get("fullName"),
            "cidade": (estadio.get("address") or {}).get("city"),
            "stats_mandante": {},
            "stats_visitante": {},
        }

        if status == "finished":
            try:
                espn_detalhar(jogo, evento["id"])
            except (requests.RequestException, KeyError, IndexError) as erro:
                print("   Detalhes indisponíveis:", erro)
            time.sleep(PAUSA)
        else:
            jogo["gols_mandante"] = jogo["gols_visitante"] = None

        jogos.append(jogo)

    return jogos


# =========================================================
# 1C. TODOS OS JOGOS DA LIGA (base da simulação do campeonato)
# =========================================================

def linha_liga(id_jogo, data, status, mandante, visitante, gols_mandante, gols_visitante):
    encerrado = status == "finished"
    return {
        "id_jogo": id_jogo,
        "data": data,
        "status": status,
        "mandante": NOMES.get(mandante, mandante),
        "visitante": NOMES.get(visitante, visitante),
        "gols_mandante": gols_mandante if encerrado else None,
        "gols_visitante": gols_visitante if encerrado else None,
    }


def liga_espn():
    """Jogos disputados e agendados de todos os clubes, pela agenda de cada um."""
    clubes = get_json(f"{ESPN_URL}/teams")["sports"][0]["leagues"][0]["teams"]
    eventos = {}
    for item in clubes:
        clube = item["team"]
        if clube["displayName"].startswith("TBD"):
            continue
        for extra in ({}, {"fixture": "true"}):
            agenda = get_json(
                f"{ESPN_URL}/teams/{clube['id']}/schedule",
                params={"season": TEMPORADA, **extra},
            )
            for evento in agenda.get("events", []):
                eventos[evento["id"]] = evento
            time.sleep(PAUSA)

    jogos = []
    for evento in eventos.values():
        competicao = evento["competitions"][0]
        lados = {c["homeAway"]: c for c in competicao["competitors"]}
        inicio = datetime.fromisoformat(evento["date"].replace("Z", "+00:00"))
        jogos.append(linha_liga(
            f"espn_{evento['id']}",
            inicio.astimezone(BRASILIA).date().isoformat(),
            espn_status(competicao.get("status", {}).get("type", {})),
            lados["home"]["team"]["displayName"],
            lados["away"]["team"]["displayName"],
            espn_placar(lados["home"].get("score")),
            espn_placar(lados["away"].get("score")),
        ))
    return jogos


def liga_fsapi():
    """Resultados de todos os clubes. Os jogos futuros não precisam vir da API: a
    simulação completa o turno e returno com os confrontos ainda não disputados."""
    params = {"league_id": SERIE_B_ID, "season": TEMPORADA, "limit": 1000, "sort": "kickoff_utc"}
    jogos, cursor = [], None
    while True:
        if cursor:
            params["cursor"] = cursor
        resposta = fsapi_get("/matches", params)
        for jogo in resposta.get("data", []):
            jogos.append(linha_liga(
                jogo["match_id"], jogo.get("kickoff_date"), jogo.get("match_status"),
                jogo.get("home_team_name"), jogo.get("away_team_name"),
                jogo.get("home_goals"), jogo.get("away_goals"),
            ))
        cursor = resposta.get("meta", {}).get("next_cursor")
        if not cursor:
            return jogos


# =========================================================
# 2. JOGO NA PERSPECTIVA DO VILA NOVA
# =========================================================

def resultado(pro, contra):
    if pro is None or contra is None:
        return None
    if pro > contra:
        return "V"
    if pro < contra:
        return "D"
    return "E"


def percentual_decimal(valor):
    """Converte percentuais da API (ex.: 63) para decimal (0.63)."""
    valor = numero(valor)
    return None if valor is None else round(valor / 100, 4)


def montar_linha(jogo):
    vn, adv = ("mandante", "visitante") if jogo["em_casa"] else ("visitante", "mandante")

    gols_vn, gols_adv = jogo[f"gols_{vn}"], jogo[f"gols_{adv}"]
    gols_1t_vn, gols_1t_adv = jogo[f"gols_1t_{vn}"], jogo[f"gols_1t_{adv}"]

    gols_2t_vn = gols_2t_adv = None
    if None not in (gols_vn, gols_adv, gols_1t_vn, gols_1t_adv):
        gols_2t_vn = gols_vn - gols_1t_vn
        gols_2t_adv = gols_adv - gols_1t_adv

    s_vn, s_adv = jogo[f"stats_{vn}"], jogo[f"stats_{adv}"]
    adversario = jogo[adv]

    return {
        "id_jogo": jogo["id_jogo"],
        "data": jogo["data"],
        "status": jogo["status"],
        "adversario": NOMES.get(adversario, adversario),
        "mando": "Casa" if jogo["em_casa"] else "Fora",
        "gols_vila_nova": gols_vn,
        "gols_adversario": gols_adv,
        "resultado": resultado(gols_vn, gols_adv),
        "gols_1t_vila_nova": gols_1t_vn,
        "gols_1t_adversario": gols_1t_adv,
        "gols_2t_vila_nova": gols_2t_vn,
        "gols_2t_adversario": gols_2t_adv,
        "resultado_intervalo": resultado(gols_1t_vn, gols_1t_adv),
        "estadio": ESTADIOS.get(jogo["estadio"], jogo["estadio"]),
        "cidade": CIDADES.get(jogo["cidade"], jogo["cidade"]),

        # VILA NOVA
        "posse_vila_nova": percentual_decimal(s_vn.get("possession_pct")),
        "finalizacoes_vila_nova": s_vn.get("shots_total"),
        "chutes_alvo_vila_nova": s_vn.get("shots_on_target"),
        "chutes_fora_vila_nova": s_vn.get("shots_off_target"),
        "chutes_bloqueados_vila_nova": s_vn.get("shots_blocked"),
        "chutes_area_vila_nova": s_vn.get("shots_inside_box"),
        "chutes_fora_area_vila_nova": s_vn.get("shots_outside_box"),
        "escanteios_vila_nova": s_vn.get("corners"),
        "faltas_vila_nova": s_vn.get("fouls"),
        "impedimentos_vila_nova": s_vn.get("offsides"),
        "passes_vila_nova": s_vn.get("passes_total"),
        "passes_certos_vila_nova": s_vn.get("passes_accurate"),
        "amarelos_vila_nova": s_vn.get("yellow_cards"),
        "vermelhos_vila_nova": s_vn.get("red_cards"),
        "defesas_vila_nova": s_vn.get("saves"),

        # ADVERSÁRIO
        "posse_adversario": percentual_decimal(s_adv.get("possession_pct")),
        "finalizacoes_adversario": s_adv.get("shots_total"),
        "chutes_alvo_adversario": s_adv.get("shots_on_target"),
        "escanteios_adversario": s_adv.get("corners"),
        "faltas_adversario": s_adv.get("fouls"),
        "passes_adversario": s_adv.get("passes_total"),
        "passes_certos_adversario": s_adv.get("passes_accurate"),
        "amarelos_adversario": s_adv.get("yellow_cards"),
        "vermelhos_adversario": s_adv.get("red_cards"),
    }


# =========================================================
# 3. DATAFRAME E MÉTRICAS
# Percentuais entre 0 e 1 (ex.: 0.7188 -> 71,88% no Power BI).
# =========================================================

def montar_dataframe(jogos):
    df = pd.DataFrame([montar_linha(jogo) for jogo in jogos])
    df = df.drop_duplicates(subset=["id_jogo"])
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.sort_values("data", kind="stable")

    contagens = [
        coluna for coluna in df.columns
        if coluna.startswith(("gols_", "finalizacoes_", "chutes_", "escanteios_", "faltas_",
                              "impedimentos_", "passes_", "amarelos_", "vermelhos_", "defesas_"))
    ]
    df[contagens] = df[contagens].apply(pd.to_numeric, errors="coerce").astype("Int64")

    for lado in ("vila_nova", "adversario"):
        passes = df[f"passes_{lado}"].replace(0, pd.NA)
        finalizacoes = df[f"finalizacoes_{lado}"].replace(0, pd.NA)
        df[f"aproveitamento_passes_{lado}"] = (df[f"passes_certos_{lado}"] / passes).astype("Float64").round(4)
        df[f"precisao_finalizacao_{lado}"] = (df[f"chutes_alvo_{lado}"] / finalizacoes).astype("Float64").round(4)
        df[f"conversao_{lado}"] = (df[f"gols_{lado}"] / finalizacoes).astype("Float64").round(4)

    df["data"] = df["data"].dt.strftime("%Y-%m-%d")
    return df


# =========================================================
# 4. EXECUÇÃO
# =========================================================

def main():
    if FSAPI_KEY:
        print("Fonte: Football Soccer API")
        jogos = coletar_fsapi()
        liga = liga_fsapi()
    else:
        print("Fonte: ESPN (defina FSAPI_KEY para usar a Football Soccer API)")
        jogos = coletar_espn()
        print("\nColetando os jogos dos demais clubes...")
        liga = liga_espn()

    df = montar_dataframe(jogos)
    df.to_csv(ARQUIVO, index=False, encoding="utf-8-sig")

    df_liga = pd.DataFrame(liga).drop_duplicates(subset=["id_jogo"]).sort_values(["data", "id_jogo"])
    for coluna in ("gols_mandante", "gols_visitante"):
        df_liga[coluna] = pd.to_numeric(df_liga[coluna], errors="coerce").astype("Int64")
    df_liga.to_csv(ARQUIVO_LIGA, index=False, encoding="utf-8-sig")
    print(f"Jogos da liga: {len(df_liga)} ({(df_liga['status'] == 'finished').sum()} encerrados) -> {ARQUIVO_LIGA}")

    encerrados = df[df["status"] == "finished"]
    print("\n" + "=" * 60)
    print("FINALIZADO")
    print("=" * 60)
    print("Jogos encontrados:", len(df))
    print("Jogos encerrados:", len(encerrados))
    print("Próximos jogos:", (df["status"] == "scheduled").sum())
    print("Jogos com placar do intervalo:", encerrados["gols_1t_vila_nova"].notna().sum())
    print("Jogos com estatísticas:", encerrados["finalizacoes_vila_nova"].notna().sum())
    print("Arquivo:", ARQUIVO)

    # Com a liga atualizada, recalcula as chances de acesso e rebaixamento.
    print("\n" + "=" * 60)
    print("SIMULAÇÃO DO CAMPEONATO")
    print("=" * 60)
    import simulacao
    simulacao.main()


if __name__ == "__main__":
    main()
