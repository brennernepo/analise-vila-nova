<p align="center">
  <img src="vila-nova-logo.png" alt="Escudo do Vila Nova" width="110">
</p>

<h1 align="center">Dashboard Gerencial — Vila Nova na Série B 2026</h1>

<p align="center">
  Projeto de análise de dados esportivos que transforma os resultados da campanha do Vila Nova em indicadores de desempenho, tendências e cenários probabilísticos.
</p>

<p align="center">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-1.64-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="JavaScript" src="https://img.shields.io/badge/JavaScript-ES6-F7DF1E?logo=javascript&logoColor=111111">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="Pandas" src="https://img.shields.io/badge/Pandas-3.0-150458?logo=pandas&logoColor=white">
</p>

![Visão geral da dashboard](dashboard-preview.png)

## Sobre o projeto

Esta dashboard acompanha a campanha do Vila Nova Futebol Clube na Série B de 2026 sob uma perspectiva gerencial. O painel consolida os resultados jogo a jogo, compara o desempenho dentro e fora de casa e converte a campanha em informações úteis para tomada de decisão.

Além dos indicadores tradicionais, o projeto apresenta projeções para as rodadas finais e um modelo probabilístico para estimar as chances de acesso, chegada ao G6 e rebaixamento.

## Panorama analisado

| Indicador | Resultado |
|---|---:|
| Posição na tabela | 1º lugar (líder) |
| Jogos disputados | 30 |
| Pontos conquistados | 54 |
| Campanha | 16 vitórias, 6 empates e 8 derrotas |
| Aproveitamento | 60,0% |
| Média de pontos | 1,80 por jogo |
| Gols | 43 marcados e 31 sofridos |
| Saldo de gols | +12 |

Os dados representam o recorte disponível até 25 de setembro de 2026 (30ª rodada). A posição na tabela foi conferida na classificação de 27 de setembro de 2026.

## Principais insights

- O Vila Nova é muito mais forte como mandante: **84,4% de aproveitamento no OBA**, contra **35,6% como visitante**.
- Dos 54 pontos conquistados, **38 foram obtidos em casa** e **16 fora**. Em 15 jogos como mandante, a única derrota foi para o Sport (0 × 1).
- Os gols se dividem por igual entre os tempos (**51,2% no primeiro** e **48,8% no segundo**), mas a defesa é mais vulnerável antes do intervalo: **18 dos 31 gols sofridos** saíram no 1º tempo.
- Fora de casa, o problema está no início das partidas: o 1º tempo como visitante tem saldo de **−8** (5 marcados e 13 sofridos), contra **+12** em casa (17 a 5).
- Quando foi para o intervalo vencendo, o time **venceu os 11 jogos**.
- Após 30 rodadas, a equipe está **9 pontos acima** do ritmo equivalente a 50% de aproveitamento.
- Mantida a média de 1,80 ponto por jogo, a projeção é encerrar a competição com aproximadamente **68 pontos**.
- O intervalo mais provável do modelo concentra 80% dos cenários entre **64 e 73 pontos**, com mediana de **68 pontos**.
- As probabilidades estimadas no recorte atual são **91,8% de acesso** (84,4% direto e 7,4% via playoffs), **99,2% de chegada ao G6** e **0% de rebaixamento**, já que a campanha superou a faixa de risco.

## O que a dashboard entrega

- KPIs de pontos, aproveitamento, média por jogo e saldo de gols;
- distribuição de vitórias, empates e derrotas;
- evolução da pontuação rodada a rodada;
- comparação entre desempenho em casa e como visitante;
- comparação de gols marcados e sofridos no primeiro e no segundo tempo;
- rendimento por períodos da competição;
- sequência recente e indicadores de consistência;
- projeção de pontuação para as 38 rodadas;
- simulação de metas de pontos;
- cenários probabilísticos de acesso, G6 e rebaixamento;
- próximos adversários, com as datas dos jogos já agendados;
- tabela completa com busca por adversário e filtros por mando de campo.

## Metodologia

### Pontuação e aproveitamento

- Vitória: 3 pontos;
- empate: 1 ponto;
- derrota: 0 ponto;
- aproveitamento: pontos conquistados ÷ pontos possíveis.

O painel considera somente partidas com <code>status</code> igual a <code>finished</code> e resultado identificado como <code>V</code>, <code>E</code> ou <code>D</code>. Jogos com <code>status</code> <code>scheduled</code> alimentam a lista de próximos adversários; sem eles, o painel espelha a tabela do primeiro turno.

### Modelo probabilístico

As probabilidades são calculadas por uma distribuição preditiva bayesiana com prior de Jeffreys, separando o desempenho como mandante e visitante e aplicando cada distribuição aos jogos restantes em casa e fora.

Referências adotadas no modelo:

- G6: 60 pontos ou mais (em 27/09, o 6º colocado projetava cerca de 61 pontos);
- acesso direto: 65 pontos ou mais (o 2º colocado projetava cerca de 65);
- acesso via playoffs: 50% da probabilidade de terminar entre 60 e 64 pontos;
- rebaixamento: 44 pontos ou menos.

Essas faixas são referências analíticas e não representam cortes garantidos. O modelo não considera a campanha dos demais clubes, critérios de desempate ou a força individual dos adversários.

## Fontes de dados

O script <code>coleta_detalhada.py</code> gera sempre o mesmo CSV a partir de uma de duas APIs REST:

- **Football Soccer API** (plano gratuito, 50 chamadas por dia): usada quando a variável <code>FSAPI_KEY</code> está definida. O script localiza o id do Vila Nova automaticamente e só detalha jogos encerrados, para caber na cota diária;
- **API pública da ESPN**: usada automaticamente quando não há chave. Não exige cadastro e traz também os jogos já agendados.

As duas fontes foram comparadas no jogo Vila Nova 4 × 3 Náutico (14ª rodada): placar, placar do intervalo, finalizações, passes, escanteios, faltas e cartões coincidem.

## Tecnologias utilizadas

- **Python e Pandas:** coleta, tratamento dos dados e criação de métricas;
- **Streamlit:** publicação e disponibilização da aplicação;
- **JavaScript:** cálculos, filtros, simulações e renderização dos gráficos;
- **HTML e CSS:** estrutura, responsividade e identidade visual;
- **CSV:** armazenamento da base consolidada;
- **GitHub:** versionamento e integração com o deploy.

## Estrutura do projeto

<pre><code>analise_vila_nova/
├── app.js
├── coleta_detalhada.py
├── dashboard-preview.png
├── index.html
├── README.md
├── requirements.txt
├── server.js
├── streamlit_app.py
├── styles.css
├── vila-nova-logo.png
└── vila_nova_serie_b_2026_todos_jogos.csv
</code></pre>

## Executar localmente

### Streamlit

<pre><code>cd analise_vila_nova
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
</code></pre>

A aplicação será disponibilizada normalmente em <code>http://localhost:8501</code>.

### Versão HTML

<pre><code>node server.js
</code></pre>

Depois, acesse <code>http://localhost:8000</code>. O <code>index.html</code> também abre direto do disco: nesse caso, o navegador bloqueia a leitura do CSV e o painel usa os dados incorporados no <code>app.js</code>, que refletem a última coleta.

## Atualização dos dados

Para atualizar a base com a API da ESPN, sem chave:

<pre><code>python coleta_detalhada.py
</code></pre>

Para usar a Football Soccer API, informe a chave por variável de ambiente no PowerShell antes da coleta:

<pre><code>$env:FSAPI_KEY="SUA_CHAVE"
python coleta_detalhada.py
</code></pre>

Se a busca automática do clube falhar, defina também <code>$env:VILA_NOVA_ID="tm_..."</code>. A chave não deve ser gravada no código nem enviada ao GitHub. Após atualizar o CSV e enviar um novo commit para a branch <code>main</code>, o Streamlit Community Cloud realiza o redeploy da aplicação.

## Publicar no Streamlit Community Cloud

1. Envie esta pasta para um repositório público no GitHub.
2. Em [share.streamlit.io](https://share.streamlit.io), escolha **Create app** e selecione o repositório.
3. Informe a branch <code>main</code> e o arquivo principal <code>streamlit_app.py</code>.
4. Clique em **Deploy**. O Streamlit instala as dependências de <code>requirements.txt</code> e gera o link público.

## Competências demonstradas

- coleta e tratamento de dados via API;
- definição e cálculo de indicadores esportivos;
- análise exploratória e comunicação de insights;
- modelagem probabilística de cenários;
- construção de dashboards responsivos;
- versionamento com Git e publicação em nuvem.

## Créditos

Adaptação para o Vila Nova do projeto [analise_nautico](https://github.com/pablohmelo02/analise_nautico), de [Pablo Melo](https://github.com/pablohmelo02). O escudo em <code>vila-nova-logo.png</code> foi obtido na ESPN e é marca do Vila Nova Futebol Clube.
