"""Extrai os números das Demonstrações Financeiras 2025 do Vila Nova para a dashboard.

Uso:
    python extrair_financas.py caminho/para/demonstracoes-contabeis-2025.pdf

Lê o balanço, a DRE, o fluxo de caixa, as notas explicativas e o quadro do
Fair Play Financeiro (SSF), confere se os totais fecham e grava financas_2025.js,
carregado pelo painel. Valores em milhares de reais, como no documento.
"""

import json
import re
import sys
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parent
PDF_PADRAO = "demonstracoes-contabeis-2025.pdf"
ARQUIVO = ROOT / "financas_2025.js"
# O próprio documento tem diferenças de arredondamento de até R$ 1 mil entre itens e totais.
TOLERANCIA = 2

NUMERO = r"\(?[\d.]+\)?|-"
LINHA = re.compile(
    rf"^(?P<conta>.*?)\s*(?:\b(?P<nota>\d{{1,2}})\s+)?(?P<atual>{NUMERO})\s+(?P<anterior>{NUMERO})$"
)
CABECALHO_ANOS = re.compile(r"^(?:Nota\s+)?20\d\d\s+20\d\d$")


# =========================================================
# 1. LEITURA DO TEXTO
# =========================================================

def valor(texto):
    """'(3.244)' -> -3244 · '5.851' -> 5851 · '-' -> 0."""
    if texto == "-":
        return 0
    negativo = texto.startswith("(")
    numero = int(texto.strip("()").replace(".", ""))
    return -numero if negativo else numero


def limpar(conta):
    conta = re.sub(r"^[A-Z]\s(?=[A-ZÁÉÍÓÚ])", "", conta)  # letra solta do texto vertical da margem
    conta = re.sub(r"^\([=\-]\)\s*", "", conta)          # "(=) Déficit..." -> "Déficit..."
    conta = re.sub(r"\s*\((?:i|ii|iii|iv|v)\)$", "", conta)  # marcadores de rodapé
    return conta.strip()


def linhas(texto):
    """Cabeçalhos (sem números) e linhas com os valores dos dois exercícios."""
    for bruta in texto.splitlines():
        linha = bruta.strip()
        if not linha or CABECALHO_ANOS.match(linha):
            continue
        achado = LINHA.match(linha)
        if achado:
            yield {
                "conta": limpar(achado["conta"]),
                "atual": valor(achado["atual"]),
                "anterior": valor(achado["anterior"]),
            }
        else:
            yield {"cabecalho": linha}


def trecho(paginas, inicio, fim=None):
    """Texto entre o título de uma demonstração ou nota e o título seguinte."""
    for texto in paginas:
        if texto.lstrip().startswith("ÍNDICE"):
            continue  # o sumário repete os títulos das seções
        posicao = re.search(inicio, texto)
        if posicao:
            resto = texto[posicao.end():]
            if fim:
                corte = re.search(fim, resto)
                resto = resto[:corte.start()] if corte else resto
            return resto
    raise ValueError(f"Trecho não encontrado no PDF: {inicio!r}")


def tabela(texto):
    """Contas rotuladas de um trecho: {conta: {"atual", "anterior"}}."""
    return {
        item["conta"]: {"atual": item["atual"], "anterior": item["anterior"]}
        for item in linhas(texto)
        if item.get("conta")
    }


def serie(item, nome=None, **extra):
    return {"nome": nome or item.get("nome"), "atual": item["atual"], "anterior": item["anterior"], **extra}


def conta(dados, padrao):
    for nome, item in dados.items():
        if re.search(padrao, nome):
            return item
    raise ValueError(f"Conta não encontrada: {padrao!r}")


def soma(itens):
    return {
        "atual": sum(item["atual"] for item in itens),
        "anterior": sum(item["anterior"] for item in itens),
    }


def exigencia(texto):
    """Reescreve o limite do quadro do SSF em linguagem corrida."""
    texto = re.sub(r"(\d)mi\b", r"\1 mi", texto)
    texto = re.sub(r"^Máx(?:imo)?:\s*Déficit\s+", "déficit máximo de ", texto)
    texto = re.sub(r"^Máx(?:imo)?:\s*", "máximo de ", texto)
    return re.sub(r"^Transição \((\d+%) Pleno\)$", r"\1 na regra plena (em transição)", texto)


def conferir(descricao, calculado, informado):
    for ano in ("atual", "anterior"):
        diferenca = abs(calculado[ano] - informado[ano])
        if diferenca > TOLERANCIA:
            raise ValueError(
                f"{descricao} não fecha ({ano}): calculado {calculado[ano]}, informado {informado[ano]}"
            )
    print(f"   OK  {descricao}")


# =========================================================
# 2. DEMONSTRAÇÕES E NOTAS
# =========================================================

def ler_grupos(texto):
    """Nota com grupos: cabeçalho, itens e um subtotal sem rótulo (ex.: nota 15)."""
    grupos, soltos, atual = [], {}, None
    for item in linhas(texto):
        if "cabecalho" in item:
            atual = {"nome": item["cabecalho"], "itens": []}
        elif item["conta"] and atual:
            atual["itens"].append(serie(item, item["conta"]))
        elif atual:
            atual.update(atual=item["atual"], anterior=item["anterior"])
            grupos.append(atual)
            atual = None
        elif item["conta"]:
            soltos[item["conta"]] = item
    return grupos, soltos


def ler_balanco(texto):
    """Balanço com as contas indexadas por lado e seção (há rótulos repetidos)."""
    contas, lado, secao = {}, None, None
    for item in linhas(texto):
        if "cabecalho" in item:
            cabecalho = re.sub(r"\s+\d{1,2}$", "", item["cabecalho"])
            if cabecalho == "Ativo":
                lado = "ativo"
            elif cabecalho.startswith("Passivo"):
                lado = "passivo"
            elif cabecalho in ("Circulante", "Não circulante", "Patrimônio social"):
                secao = cabecalho
            continue
        chave = item["conta"] or "Subtotal"
        contas[(lado, secao, chave)] = item
        if item["conta"].startswith("Total"):
            contas[(lado, "Total", "Total")] = item
    return contas


def extrair(caminho_pdf):
    with pdfplumber.open(caminho_pdf) as pdf:
        paginas = [pagina.extract_text() or "" for pagina in pdf.pages]
    print(f"PDF: {caminho_pdf} ({len(paginas)} páginas)")

    dre = tabela(trecho(paginas, r"Demonstração do resultado\s*\n\s*Exercícios", r"As notas explicativas"))
    balanco = ler_balanco(trecho(paginas, r"Balanço Patrimonial", r"As notas explicativas"))
    fluxo = tabela(trecho(paginas, r"Demonstração dos fluxos de caixa", r"As notas explicativas"))
    grupos, receitas_soltas = ler_grupos(trecho(paginas, r"15\.\s+Receita operacional líquida", r"16\.\s+Custo"))
    custo_itens = [
        serie(item, item["conta"])
        for item in linhas(trecho(paginas, r"16\.\s+Custo das atividades esportivas", r"\(i\) Refere-se"))
        if item.get("conta")
    ]
    custo_total = [
        item for item in linhas(trecho(paginas, r"16\.\s+Custo das atividades esportivas", r"\(i\) Refere-se"))
        if "conta" in item and not item["conta"]
    ][-1]
    outras = tabela(trecho(paginas, r"19\.\s+Outras receitas, líquidas", r"www\.vilanovafc"))
    intangivel = tabela(trecho(paginas, r"Direitos econômicos - Movimentação", r"\(i\) Adições"))
    trabalhistas = tabela(trecho(paginas, r"9\.\s+Obrigações trabalhistas e sociais", r"\(i\) Dívida"))
    tributarias = tabela(trecho(paginas, r"10\.\s+Obrigações tributárias", r"\(i\) Dívida"))
    outras_contas = tabela(trecho(paginas, r"11\.\s+Outras contas a pagar", r"\(i\) Débitos"))
    ssf_texto = trecho(paginas, r"Indicador Estratégico SSF", r"www\.vilanovafc")
    caixa_texto = trecho(paginas, r"Evolução do Caixa e Endividamento", r"INDICADORES-CHAVE")
    ssf_cronograma = trecho(paginas, r"Cronograma SSF", r"Indicador Estratégico SSF")

    print("Conferências:")

    # --- Receitas (nota 15) e venda de atletas (nota 19) ---
    for grupo in grupos:
        conferir(f"Receita · {grupo['nome']}", soma(grupo["itens"]), grupo)
    deducoes = conta(receitas_soltas, r"^Impostos e deduções")
    receita_liquida = conta(dre, r"^Receita operacional líquida")
    conferir("Receita líquida (nota 15 x DRE)", soma(grupos + [deducoes]), receita_liquida)
    receita_bruta = soma(grupos)
    venda_atletas = conta(outras, r"^Movimentação de atletas")
    lfu = next(i for g in grupos for i in g["itens"] if i["nome"].startswith("Adesão ao condomínio LFU"))

    # --- Custo do futebol (nota 16) ---
    custo_dre = conta(dre, r"^Custo das atividades")
    conferir("Custo das atividades esportivas (nota 16)", soma(custo_itens), custo_total)
    conferir("Custo das atividades esportivas (nota 16 x DRE)", custo_total, custo_dre)

    # --- DRE ---
    bruto = conta(dre, r"^Resultado Bruto")
    pessoal = conta(dre, r"^Despesas com pessoal")
    gerais = conta(dre, r"^Despesas com atividades gerais")
    outras_liquidas = conta(dre, r"^Outras receitas, líquidas")
    operacional = conta(dre, r"^Superávit operacional|^Déficit operacional")
    despesas_fin = conta(dre, r"^Despesas financeiras")
    receitas_fin = conta(dre, r"^Receitas financeiras")
    financeiro = conta(dre, r"^Resultado financeiro líquido")
    resultado = conta(dre, r"^(Déficit|Superávit) do Exercício")
    conferir("Resultado bruto", soma([receita_liquida, custo_dre]), bruto)
    conferir("Resultado operacional", soma([bruto, pessoal, gerais, outras_liquidas]), operacional)
    conferir("Resultado financeiro", soma([despesas_fin, receitas_fin]), financeiro)
    conferir("Resultado do exercício", soma([operacional, financeiro]), resultado)
    conferir("Outras receitas líquidas (nota 19 x DRE)", conta(outras, r"^Outras receitas, líquidas"), outras_liquidas)

    # --- Balanço ---
    ativo_total = balanco[("ativo", "Total", "Total")]
    passivo_circulante = balanco[("passivo", "Circulante", "Subtotal")]
    passivo_nao_circulante = balanco[("passivo", "Não circulante", "Subtotal")]
    patrimonio = balanco[("passivo", "Patrimônio social", "Subtotal")]
    conferir("Balanço (ativo = passivo + patrimônio)", soma([passivo_circulante, passivo_nao_circulante, patrimonio]), ativo_total)
    subvencoes = balanco[("passivo", "Não circulante", "Subvenções recebidas")]
    emprestimos = soma([
        balanco[("passivo", "Circulante", "Empréstimos e financiamentos")],
        balanco[("passivo", "Não circulante", "Empréstimos e financiamentos")],
    ])

    # --- Dívida: passivo total sem as subvenções recebidas (critério do relatório da administração) ---
    divida_total = {
        ano: passivo_circulante[ano] + passivo_nao_circulante[ano] - subvencoes[ano]
        for ano in ("atual", "anterior")
    }
    mutuos = conta(outras_contas, r"^Débitos com conselheiros")
    obrig_trab = balanco[("passivo", "Circulante", "Obrigações trabalhistas e sociais")]
    obrig_trib = balanco[("passivo", "Circulante", "Obrigações tributárias")]
    transf = balanco[("passivo", "Circulante", "Contas a pagar com a transferência de jogadores")]
    principais = [mutuos, obrig_trab, obrig_trib, transf]
    outros_passivos = {ano: divida_total[ano] - sum(i[ano] for i in principais) for ano in ("atual", "anterior")}
    div_prev = conta(trabalhistas, r"^Dívida ativa previdenciária")
    div_fiscal = conta(tributarias, r"^Débitos em dívida ativa")

    # --- Fluxo de caixa ---
    fc_operacional = conta(fluxo, r"^Caixa líquido.*operacionais")
    fc_investimentos = conta(fluxo, r"^Caixa líquido.*investimentos")
    fc_financiamentos = conta(fluxo, r"^Caixa líquido.*financiamentos")
    caixa_inicial = conta(fluxo, r"^Caixa no início")
    caixa_final = conta(fluxo, r"^Caixa no final")
    conferir(
        "Fluxo de caixa (variação = final - inicial)",
        soma([fc_operacional, fc_investimentos, fc_financiamentos]),
        {ano: caixa_final[ano] - caixa_inicial[ano] for ano in ("atual", "anterior")},
    )
    conferir("Caixa final (fluxo x balanço)", caixa_final, balanco[("ativo", "Circulante", "Caixa e equivalentes de caixa")])

    # --- Direitos econômicos de atletas (nota 6) ---
    saldo_inicial = conta(intangivel, r"^Saldo inicial")
    adicoes = conta(intangivel, r"^Adições")
    baixas = conta(intangivel, r"^Baixas")
    amortizacoes = conta(intangivel, r"^Amortizações")
    saldo_final = conta(intangivel, r"^Saldo Final")
    conferir("Intangível (movimentação)", soma([saldo_inicial, adicoes, baixas, amortizacoes]), saldo_final)
    conferir("Intangível (nota 6 x balanço)", saldo_final, balanco[("ativo", "Não circulante", "Intangível")])

    # --- Fair Play Financeiro (SSF), do relatório da administração ---
    ssf = []
    padrao_ssf = re.compile(
        r"^(?:\S\s)?\d\.\s(?P<indicador>.+?)\s(?P<apurado>(?:Superávit|Déficit)\sR\$\s[\d,]+\s?mi|[\d,]+%)"
        r"\s(?P<limite>.+?)\s(?P<status>NÃO CONFORME|CONFORME)$"
    )
    for linha in ssf_texto.splitlines():
        achado = padrao_ssf.match(linha.strip())
        if achado:
            ssf.append({
                "indicador": achado["indicador"],
                "apurado": re.sub(r"R\$\s([\d,]+)\s?mi", r"R$ \1 mi", achado["apurado"]),
                "limite": exigencia(achado["limite"]),
                "conforme": achado["status"] == "CONFORME",
            })
    if len(ssf) != 4:
        raise ValueError(f"Quadro do SSF incompleto: {len(ssf)} indicadores lidos")
    limites_ssf = [
        {"ano": ano, "limite": int(limite)}
        for ano, limite in re.findall(r"(20\d\d)\+?\s+(?:Endiv\. CP: limite|Limite definitivo)\s+(\d+)%", ssf_cronograma)
    ]
    print("   OK  Quadro do SSF (4 indicadores)")

    waiver = re.search(r"aproximadamente R\$ ([\d,]+) milhões", caixa_texto)

    def grupo(nome):
        return next(g for g in grupos if g["nome"].startswith(nome))

    def item(nome):
        return next(i for g in grupos for i in g["itens"] if i["nome"].startswith(nome))

    return {
        "exercicio": 2025,
        "comparativo": 2024,
        "fonte": "Relatório Anual da Administração e Demonstrações Financeiras 2025 do Vila Nova Futebol Clube",
        "faturamento": soma([receita_bruta, venda_atletas]),
        "receita_liquida": receita_liquida,
        "receita_recorrente": {ano: receita_liquida[ano] - lfu[ano] for ano in ("atual", "anterior")},
        "venda_atletas": venda_atletas,
        "receitas": [
            serie(grupo("Diversos"), "Diversos (inclui LFU)", detalhe="Adesão à LFU, quadro social, loterias e bares"),
            serie(grupo("Patrocínio"), "Patrocínio e licenciamento", detalhe="Patrocínios, publicidade e royalties"),
            serie(venda_atletas, "Venda de atletas", detalhe="Resultado líquido das negociações"),
            serie(grupo("Mídia"), "Mídia e publicidade", detalhe="Participação em competições e TV"),
            serie(grupo("Operações de jogos"), "Operações de jogos", detalhe="Bilheteria e Sócio Tigrão"),
        ],
        "destaques_receita": [
            serie(item("Bilheteria"), "Bilheteria"),
            serie(item("Patrocínios e publicidade"), "Patrocínios e publicidade"),
            serie(lfu, "Adesão à LFU"),
            serie(item("Direitos de transmissão"), "Direitos de transmissão"),
        ],
        "custos": [
            serie(custo_dre, "Custo do futebol", detalhe="Elenco, premiações, jogos e amortização"),
            serie(gerais, "Despesas gerais", detalhe="Serviços, consumo, esportes olímpicos"),
            serie(despesas_fin, "Despesas financeiras", detalhe="Juros e encargos"),
            serie(pessoal, "Pessoal (administração e base)", detalhe="Salários fora do futebol profissional"),
        ],
        "custo_futebol": custo_itens,
        "dre": [
            serie(receita_liquida, "Receita operacional líquida", tipo="total"),
            serie(custo_dre, "Custo das atividades esportivas"),
            serie(bruto, "Resultado bruto", tipo="subtotal"),
            serie(pessoal, "Despesas com pessoal"),
            serie(gerais, "Despesas gerais"),
            serie(outras_liquidas, "Outras receitas líquidas"),
            serie(operacional, "Resultado operacional", tipo="subtotal"),
            serie(financeiro, "Resultado financeiro"),
            serie(resultado, "Resultado do exercício", tipo="total"),
        ],
        "resultado": resultado,
        "divida": {
            "total": divida_total,
            "itens": [
                serie(mutuos, "Mútuos com conselheiros", detalhe="Sem juros em 2025 (waiver)"),
                serie(obrig_trab, "Obrigações trabalhistas", detalhe=f"Dívida ativa previdenciária de R$ {div_prev['atual'] / 1000:.1f} mi".replace(".", ",")),
                serie(outros_passivos, "Outros passivos", detalhe="Provisões, empréstimos e antecipações"),
                serie(obrig_trib, "Obrigações tributárias", detalhe=f"Dívida ativa fiscal de R$ {div_fiscal['atual'] / 1000:.1f} mi".replace(".", ",")),
                serie(transf, "Transferência de jogadores", detalhe="A pagar por contratações"),
            ],
        },
        "balanco": {
            "ativo_total": ativo_total,
            "patrimonio_social": patrimonio,
            "emprestimos": emprestimos,
            "subvencoes": subvencoes,
        },
        "caixa": {
            "atividades": [
                serie(fc_operacional, "Operacional", detalhe="Gerado pelo dia a dia do clube"),
                serie(fc_investimentos, "Investimentos", detalhe="Quase tudo em direitos de atletas"),
                serie(fc_financiamentos, "Financiamentos", detalhe="Empréstimos captados menos pagos"),
            ],
            "inicial": caixa_inicial,
            "final": caixa_final,
            "aquisicao_atletas": conta(fluxo, r"^Aquisição de dire.?tos econômicos"),
            "captacao": conta(fluxo, r"^Captação de empréstimos"),
        },
        "elenco": {
            "saldo_inicial": saldo_inicial,
            "adicoes": adicoes,
            "baixas": baixas,
            "amortizacoes": amortizacoes,
            "saldo_final": saldo_final,
        },
        "waiver_mi": float(waiver.group(1).replace(",", ".")) if waiver else None,
        "ssf": ssf,
        "ssf_limites": limites_ssf,
    }


# =========================================================
# 3. EXECUÇÃO
# =========================================================

def main():
    if len(sys.argv) > 1:
        caminho = Path(sys.argv[1])
    else:
        candidatos = sorted(ROOT.glob("demonstracoes-contabeis-2025*.pdf"))
        caminho = candidatos[0] if candidatos else ROOT / PDF_PADRAO
    if not caminho.exists():
        raise SystemExit(f"PDF não encontrado: {caminho}\nUso: python extrair_financas.py caminho/do/arquivo.pdf")

    dados = extrair(caminho)
    conteudo = json.dumps(dados, ensure_ascii=False, indent=2)
    ARQUIVO.write_text(
        "// Gerado por extrair_financas.py a partir das Demonstrações Financeiras 2025 (R$ mil).\n"
        "// Para atualizar, rode o script novamente em vez de editar este arquivo.\n"
        f"window.VILA_NOVA_FINANCAS = {conteudo};\n",
        encoding="utf-8",
    )
    print(f"\nArquivo gerado: {ARQUIVO.name}")


if __name__ == "__main__":
    main()
