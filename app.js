let matches = [
  ['2026-03-21','CRB','Casa',2,2,'E'],
  ['2026-04-01','Sport','Fora',1,1,'E'],
  ['2026-04-04','Atlético Goianiense','Casa',2,1,'V'],
  ['2026-04-11','Ponte Preta','Fora',1,0,'V'],
  ['2026-04-18','Operário-PR','Casa',2,1,'V'],
  ['2026-04-26','Ceará','Fora',3,3,'E'],
  ['2026-05-04','Athletic Club','Casa',1,1,'E'],
  ['2026-05-09','Goiás','Fora',0,1,'D'],
  ['2026-05-17','Avaí','Casa',2,0,'V'],
  ['2026-05-24','América Mineiro','Fora',2,1,'V'],
  ['2026-05-31','Londrina','Fora',1,0,'V'],
  ['2026-06-08','Botafogo-SP','Casa',1,0,'V'],
  ['2026-06-14','Cuiabá','Fora',0,1,'D'],
  ['2026-06-20','Náutico','Casa',4,3,'V'],
  ['2026-06-26','Novorizontino','Fora',1,2,'D'],
  ['2026-07-06','São Bernardo','Casa',2,1,'V'],
  ['2026-07-10','Juventude','Fora',0,1,'D'],
  ['2026-07-18','Criciúma','Fora',0,2,'D'],
  ['2026-07-21','Fortaleza','Casa',2,1,'V'],
  ['2026-07-27','CRB','Fora',0,2,'D'],
  ['2026-08-08','Sport','Casa',0,1,'D'],
  ['2026-08-15','Atlético Goianiense','Fora',2,0,'V'],
  ['2026-08-19','Ponte Preta','Casa',6,0,'V'],
  ['2026-08-23','Operário-PR','Fora',0,0,'E'],
  ['2026-08-30','Ceará','Casa',2,0,'V'],
  ['2026-09-04','Athletic Club','Fora',0,5,'D'],
  ['2026-09-10','Goiás','Casa',2,0,'V'],
  ['2026-09-14','Avaí','Fora',1,1,'E'],
  ['2026-09-18','América Mineiro','Casa',1,0,'V'],
  ['2026-09-25','Londrina','Casa',2,0,'V']
].map((m, i) => ({ round: i + 1, date: m[0], opponent: m[1], venue: m[2], gf: m[3], ga: m[4], result: m[5], points: m[5] === 'V' ? 3 : m[5] === 'E' ? 1 : 0 }));

const halfTimeScores = [
  [0,1], [0,0], [0,1], [1,0], [1,1], [1,3], [0,0],
  [0,0], [2,0], [0,1], [0,0], [1,0], [0,0], [4,1],
  [1,1], [1,0], [0,1], [0,1], [2,0], [0,2], [0,1],
  [1,0], [3,0], [0,0], [1,0], [0,3], [0,0], [1,1],
  [1,0], [1,0]
];

matches = matches.map((match, index) => {
  const [htGf, htGa] = halfTimeScores[index];
  return {...match, htGf, htGa, shGf: match.gf - htGf, shGa: match.ga - htGa};
});

let upcoming = [
  ['2026-10-03','Botafogo-SP','Fora'],
  ['2026-10-07','Cuiabá','Casa'],
  ['2026-10-11','Náutico','Fora'],
  ['2026-10-18','Novorizontino','Casa'],
  ['2026-10-23','São Bernardo','Fora'],
  ['2026-10-30','Juventude','Casa'],
  ['2026-11-06','Criciúma','Casa'],
  ['2026-11-14','Fortaleza','Fora']
].map(f => ({ date: f[0], opponent: f[1], venue: f[2] }));

const $ = (id) => document.getElementById(id);
const oneDecimal = (n) => n.toLocaleString('pt-BR', {minimumFractionDigits: 1, maximumFractionDigits: 1});
const pct = (n) => `${oneDecimal(n)}%`;
const decimal = (n) => n.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const noun = (n, singular, pluralForm) => n === 1 ? singular : pluralForm;
const plural = (n, singular, pluralForm) => `${n} ${noun(n, singular, pluralForm)}`;
const formatDate = (date) => new Intl.DateTimeFormat('pt-BR', {day: '2-digit', month: 'short'}).format(new Date(`${date}T12:00:00`)).replace('.', '');
let activeFilter = 'Todos';
const MODEL_LIMITS = {relegation: 44, playoff: 60, direct: 65};
// Rótulos das probabilidades: [limite superior, texto].
const ACCESS_LEVELS = [[.10, 'BAIXA'], [.35, 'POSSÍVEL'], [.65, 'EM ABERTO'], [.90, 'ALTA'], [Infinity, 'MUITO ALTA']];
const PLAYOFF_LEVELS = [[.10, 'DESAFIO ALTO'], [.35, 'DESAFIO'], [.65, 'EM ABERTO'], [.90, 'PROVÁVEL'], [Infinity, 'MUITO PROVÁVEL']];
const RELEGATION_LEVELS = [[.10, 'RISCO BAIXO'], [.30, 'ATENÇÃO'], [.60, 'RISCO ALTO'], [Infinity, 'RISCO CRÍTICO']];

function summarize(list) {
  const wins = list.filter(m => m.result === 'V').length;
  const draws = list.filter(m => m.result === 'E').length;
  const losses = list.filter(m => m.result === 'D').length;
  const points = list.reduce((sum, m) => sum + m.points, 0);
  const gf = list.reduce((sum, m) => sum + m.gf, 0);
  const ga = list.reduce((sum, m) => sum + m.ga, 0);
  const max = list.length * 3;
  return { games: list.length, wins, draws, losses, points, gf, ga, max, efficiency: max ? points / max * 100 : 0, ppg: list.length ? points / list.length : 0 };
}

function renderSummary(list) {
  const s = summarize(list);
  $('headerGames').textContent = `${matches.length} de 38`;
  $('headerStartDate').textContent = formatDate(matches[0].date);
  $('headerEndDate').textContent = formatDate(matches.at(-1).date);
  $('kpiEfficiency').textContent = pct(s.efficiency);
  $('efficiencyMeter').style.width = `${s.efficiency}%`;
  $('efficiencyDetail').textContent = `${s.points} de ${s.max} pontos possíveis`;
  $('kpiWins').textContent = s.wins;
  $('kpiDraws').textContent = s.draws;
  $('kpiLosses').textContent = s.losses;
  $('kpiPpg').textContent = decimal(s.ppg);
  $('ppgMeter').style.width = `${Math.min(s.ppg / 3 * 100, 100)}%`;
  $('kpiGoalDiff').textContent = `${s.gf - s.ga > 0 ? '+' : ''}${s.gf - s.ga}`;
  $('goalsFor').textContent = s.gf;
  $('goalsAgainst').textContent = s.ga;
  $('winsCount').textContent = s.wins;
  $('drawsCount').textContent = s.draws;
  $('lossesCount').textContent = s.losses;
  $('donutEfficiency').textContent = pct(s.efficiency);
  $('winsPercent').textContent = pct(s.games ? s.wins / s.games * 100 : 0);
  $('drawsPercent').textContent = pct(s.games ? s.draws / s.games * 100 : 0);
  $('lossesPercent').textContent = pct(s.games ? s.losses / s.games * 100 : 0);
  $('winRate').textContent = pct(s.games ? s.wins / s.games * 100 : 0);
  $('nonLossRate').textContent = pct(s.games ? (s.wins + s.draws) / s.games * 100 : 0);
  const winDeg = s.games ? s.wins / s.games * 360 : 0;
  const drawDeg = s.games ? s.draws / s.games * 360 : 0;
  $('resultDonut').style.background = `conic-gradient(var(--red) 0 ${winDeg}deg, var(--gold) ${winDeg}deg ${winDeg + drawDeg}deg, #b9b6b0 ${winDeg + drawDeg}deg 360deg)`;
  $('filterContext').textContent = activeFilter === 'Todos' ? 'Visão geral da campanha' : `${s.games} partidas como ${activeFilter === 'Casa' ? 'mandante' : 'visitante'}`;
}

function renderChart(list) {
  if (!list.length) return;
  const w = 700, h = 285, pad = {l: 36, r: 16, t: 18, b: 32};
  let acc = 0;
  const points = list.map(m => ({x: m.round, y: (acc += m.points)}));
  const maxY = Math.max(45, Math.ceil(points.at(-1).y / 10) * 10);
  const xAt = (round) => pad.l + (round - 1) / Math.max(matches.length - 1, 1) * (w - pad.l - pad.r);
  const yAt = (value) => h - pad.b - value / maxY * (h - pad.t - pad.b);
  const actualPath = points.map((p, i) => `${i ? 'L' : 'M'} ${xAt(p.x).toFixed(1)} ${yAt(p.y).toFixed(1)}`).join(' ');
  const pacePath = `M ${xAt(1)} ${yAt(1.5)} L ${xAt(matches.length)} ${yAt(matches.length * 1.5)}`;
  const grid = [0, .25, .5, .75, 1].map(f => {
    const y = yAt(maxY * f), val = Math.round(maxY * f);
    return `<line x1="${pad.l}" y1="${y}" x2="${w-pad.r}" y2="${y}" stroke="#e4ded4" stroke-width="1"/><text x="0" y="${y+4}" fill="#89847c" font-size="10">${val}</text>`;
  }).join('');
  const area = `${actualPath} L ${xAt(points.at(-1).x)} ${h-pad.b} L ${xAt(points[0].x)} ${h-pad.b} Z`;
  const ticks = [1, 5, 10, 15, 20, 25, 30, 35].filter(r => r < matches.length - 1).concat(matches.length);
  // Os rótulos ficam do lado oposto ao da outra linha para não se sobreporem.
  const abovePace = points.at(-1).y >= matches.length * 1.5;
  const teamLabelY = yAt(points.at(-1).y) + (abovePace ? -35 : 9);
  const paceLabelY = yAt(matches.length * 1.5) + (abovePace ? 12 : -33);
  $('pointsChart').innerHTML = `<svg viewBox="0 0 ${w} ${h}" aria-hidden="true">
    <defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cc2229" stop-opacity=".18"/><stop offset="1" stop-color="#cc2229" stop-opacity="0"/></linearGradient></defs>
    ${grid}<path d="${pacePath}" fill="none" stroke="#a9a39a" stroke-width="2" stroke-dasharray="6 7"/>
    <path d="${area}" fill="url(#areaFill)"/><path d="${actualPath}" fill="none" stroke="#cc2229" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
    ${points.map((p,i) => `<circle cx="${xAt(p.x)}" cy="${yAt(p.y)}" r="${i===points.length-1?5:2.4}" fill="${i===points.length-1?'#fff':'#cc2229'}" stroke="#cc2229" stroke-width="${i===points.length-1?3:0}"><title>Rodada ${p.x}: ${p.y} pontos</title></circle>`).join('')}
    ${ticks.map(r => `<text x="${xAt(r)}" y="${h-7}" text-anchor="middle" fill="#89847c" font-size="10">R${r}</text>`).join('')}
    <g transform="translate(${xAt(points.at(-1).x)-45},${teamLabelY})"><rect width="51" height="26" rx="8" fill="#cc2229"/><text x="25.5" y="17" fill="white" text-anchor="middle" font-size="11" font-weight="800">${points.at(-1).y} pts</text></g>
    <g transform="translate(${xAt(matches.length)-111},${paceLabelY})"><rect width="59" height="22" rx="7" fill="#fff" stroke="#aaa6a0"/><text x="29.5" y="15" fill="#77736d" text-anchor="middle" font-size="9" font-weight="700">${(matches.length*1.5).toLocaleString('pt-BR')} pts</text></g>
  </svg>`;
  const full = summarize(matches);
  const pacePoints = matches.length * 1.5;
  const delta = full.points - pacePoints;
  $('chartCurrentPoints').textContent = `${full.points} pts`;
  $('chartPacePoints').textContent = `${pacePoints.toLocaleString('pt-BR')} pts`;
  $('chartGap').textContent = `${delta > 0 ? '+' : ''}${delta.toLocaleString('pt-BR')} pts`;
  $('chartGapCard').classList.toggle('positive', delta >= 0);
  $('chartInsight').innerHTML = `Após ${matches.length} rodadas, o Vila Nova está <b>${Math.abs(delta).toLocaleString('pt-BR')} ponto${Math.abs(delta) === 1 ? '' : 's'} ${delta >= 0 ? 'acima' : 'abaixo'}</b> do ritmo de 50% de aproveitamento.`;
}

function renderForm(list) {
  const recent = list.slice(-5);
  $('recentForm').innerHTML = recent.map(m => `<i class="${m.result}" title="${m.opponent}: ${m.gf} x ${m.ga}">${m.result}</i>`).join('');
  const points = recent.reduce((s,m) => s + m.points, 0);
  $('recentPoints').textContent = `${points}/${recent.length * 3} pts`;
}

function renderVenue() {
  const home = summarize(matches.filter(m => m.venue === 'Casa'));
  const away = summarize(matches.filter(m => m.venue === 'Fora'));
  const card = (name, subtitle, icon, s, cls='') => {
    const goalDiff = s.gf - s.ga;
    return `<article class="venue-card ${cls}">
      <div class="venue-card-head"><div><i>${icon}</i><span><b>${name}</b><small>${subtitle}</small></span></div><strong>${pct(s.efficiency)}</strong></div>
      <div class="venue-progress"><i style="width:${s.efficiency}%"></i></div>
      <div class="venue-stats">
        <div><span>Pontos</span><b>${s.points}</b></div>
        <div><span>Por jogo</span><b>${decimal(s.ppg)}</b></div>
        <div><span>Saldo</span><b>${goalDiff > 0 ? '+' : ''}${goalDiff}</b></div>
      </div>
      <div class="venue-record"><span><b>${s.wins}</b> ${noun(s.wins, 'vitória', 'vitórias')}</span><span><b>${s.draws}</b> ${noun(s.draws, 'empate', 'empates')}</span><span><b>${s.losses}</b> ${noun(s.losses, 'derrota', 'derrotas')}</span></div>
    </article>`;
  };
  const totalPoints = home.points + away.points;
  const homeShare = totalPoints ? home.points / totalPoints * 100 : 0;
  const awayShare = 100 - homeShare;
  $('venueComparison').innerHTML = `
    <div class="venue-cards">${card('Em casa', 'No OBA', 'C', home)}${card('Como visitante', 'Fora do OBA', 'F', away, 'away')}</div>
    <div class="venue-deep-dive">
      <div class="points-origin">
        <div class="venue-detail-head"><span>ORIGEM DOS ${totalPoints} PONTOS</span><b>${pct(homeShare)} em casa</b></div>
        <div class="split-points"><i style="width:${homeShare}%"></i><i style="width:${awayShare}%"></i></div>
        <div class="split-labels"><span><b>${home.points}</b> casa</span><span><b>${away.points}</b> fora</span></div>
      </div>
      <div class="goal-balance">
        <div class="venue-detail-head"><span>BALANÇO DE GOLS</span><b>${home.gf + away.gf} marcados</b></div>
        <div class="goal-balance-rows">
          <span><i class="home-dot"></i>Casa <b>${home.gf} pró · ${home.ga} contra</b></span>
          <span><i></i>Fora <b>${away.gf} pró · ${away.ga} contra</b></span>
        </div>
      </div>
    </div>`;
  const better = home.efficiency >= away.efficiency ? ['em casa', home, away] : ['fora de casa', away, home];
  $('venueInsight').innerHTML = `<span>LEITURA DO MANDO</span><p>O Vila Nova rende melhor <b>${better[0]}</b>: são <strong>${oneDecimal(Math.abs(better[1].efficiency - better[2].efficiency))}</strong> pontos percentuais de diferença.</p>`;
}

function renderProjection() {
  const s = summarize(matches);
  const remaining = 38 - s.games;
  const projected = Math.round(s.ppg * 38);
  $('projectedPoints').textContent = `${projected} pts`;
  $('projectionCopy').innerHTML = `Mantendo a média atual de <b>${decimal(s.ppg)} ${s.ppg >= 2 ? 'pontos' : 'ponto'} por jogo</b>, a projeção é terminar as 38 rodadas com aproximadamente <b>${projected} pontos</b>. ${remaining === 1 ? 'Resta 1 partida' : `Restam ${remaining} partidas`}.`;
  $('remainingFixtures').innerHTML = getRemainingFixtures().map(fixture => `<span class="fixture-chip"${fixture.date ? ` title="${formatDate(fixture.date)}"` : ''}><b>${fixture.venue === 'Casa' ? 'C' : 'F'}</b> ${fixture.opponent}</span>`).join('');
  $('remainingTitle').textContent = remaining > 1 ? `As ${remaining} rodadas finais` : remaining === 1 ? 'A rodada final' : 'Campanha encerrada';
  setupTargetSlider(s.points, remaining);
  updateScenario();
}

function setupTargetSlider(current, remaining) {
  const slider = $('targetPoints');
  slider.min = remaining ? current + 1 : current;
  slider.max = current + remaining * 3;
  slider.value = Math.min(Math.max(MODEL_LIMITS.direct, Number(slider.min)), Number(slider.max));
  slider.disabled = !remaining;
}

function getRemainingFixtures() {
  // Jogos já agendados na base têm prioridade; sem eles, espelha o primeiro turno.
  if (upcoming.length) return upcoming;
  const fixtures = [];
  for (let round = matches.length + 1; round <= 38; round++) {
    if (round > 19) {
      const firstLeg = matches[round - 20];
      if (firstLeg) fixtures.push({
        round,
        opponent: firstLeg.opponent,
        venue: firstLeg.venue === 'Casa' ? 'Fora' : 'Casa'
      });
    }
  }
  return fixtures;
}

function factorial(n) {
  let value = 1;
  for (let i = 2; i <= n; i++) value *= i;
  return value;
}

function rising(value, n) {
  let result = 1;
  for (let i = 0; i < n; i++) result *= value + i;
  return result;
}

function predictivePointsDistribution(games, summary) {
  const alpha = [summary.wins + .5, summary.draws + .5, summary.losses + .5];
  const alphaTotal = alpha.reduce((sum, value) => sum + value, 0);
  const distribution = new Map();
  for (let wins = 0; wins <= games; wins++) {
    for (let draws = 0; draws <= games - wins; draws++) {
      const losses = games - wins - draws;
      const arrangements = factorial(games) / factorial(wins) / factorial(draws) / factorial(losses);
      const probability = arrangements
        * rising(alpha[0], wins) * rising(alpha[1], draws) * rising(alpha[2], losses)
        / rising(alphaTotal, games);
      const points = wins * 3 + draws;
      distribution.set(points, (distribution.get(points) || 0) + probability);
    }
  }
  return distribution;
}

function buildFinishDistribution() {
  const current = summarize(matches).points;
  const fixtures = getRemainingFixtures();
  const homeGames = fixtures.filter(f => f.venue === 'Casa').length;
  const awayGames = fixtures.length - homeGames;
  const home = predictivePointsDistribution(homeGames, summarize(matches.filter(m => m.venue === 'Casa')));
  const away = predictivePointsDistribution(awayGames, summarize(matches.filter(m => m.venue === 'Fora')));
  const final = new Map();
  for (const [homePoints, homeProbability] of home) {
    for (const [awayPoints, awayProbability] of away) {
      const total = current + homePoints + awayPoints;
      final.set(total, (final.get(total) || 0) + homeProbability * awayProbability);
    }
  }
  return final;
}

function distributionProbability(distribution, predicate) {
  return [...distribution].reduce((sum, [points, probability]) => sum + (predicate(points) ? probability : 0), 0);
}

function distributionQuantile(distribution, target) {
  let cumulative = 0;
  for (const [points, probability] of [...distribution].sort((a, b) => a[0] - b[0])) {
    cumulative += probability;
    if (cumulative >= target) return points;
  }
  return Math.max(...distribution.keys());
}

function modelPercent(probability) {
  const value = probability * 100;
  if (value > 0 && value < .1) return '<0,1%';
  if (value < 100 && value > 99.9) return '>99,9%';
  return pct(value);
}

function levelLabel(probability, levels) {
  return levels.find(([limit]) => probability < limit)[1];
}

function renderProbabilities() {
  const distribution = buildFinishDistribution();
  const relegation = distributionProbability(distribution, points => points <= MODEL_LIMITS.relegation);
  const playoff = distributionProbability(distribution, points => points >= MODEL_LIMITS.playoff);
  const direct = distributionProbability(distribution, points => points >= MODEL_LIMITS.direct);
  const playoffAccess = Math.max(0, playoff - direct) * .5;
  const access = direct + playoffAccess;
  const q10 = distributionQuantile(distribution, .10);
  const median = distributionQuantile(distribution, .50);
  const q90 = distributionQuantile(distribution, .90);
  const currentPoints = summarize(matches).points;
  const available = (38 - matches.length) * 3;
  const directNeeded = Math.max(0, MODEL_LIMITS.direct - currentPoints);
  const playoffNeeded = Math.max(0, MODEL_LIMITS.playoff - currentPoints);
  const safetyNeeded = Math.max(0, MODEL_LIMITS.relegation + 1 - currentPoints);

  $('accessProbability').textContent = modelPercent(access);
  $('playoffProbability').textContent = modelPercent(playoff);
  $('relegationProbability').textContent = modelPercent(relegation);
  $('accessLevel').textContent = levelLabel(access, ACCESS_LEVELS);
  $('playoffLevel').textContent = playoffNeeded ? levelLabel(playoff, PLAYOFF_LEVELS) : 'META ATINGIDA';
  $('relegationLevel').textContent = safetyNeeded ? levelLabel(relegation, RELEGATION_LEVELS) : 'SEM RISCO';
  $('directProbability').textContent = modelPercent(direct);
  $('playoffAccessProbability').textContent = modelPercent(playoffAccess);
  $('survivalProbability').textContent = modelPercent(1 - relegation);
  $('playoffPointsNeeded').textContent = playoffNeeded ? `${playoffNeeded} pts` : 'Atingido';
  $('safetyPointsNeeded').textContent = safetyNeeded ? `${safetyNeeded} pts` : 'Atingido';
  $('accessBar').style.width = `${Math.max(access * 100, .5)}%`;
  $('playoffBar').style.width = `${Math.max(playoff * 100, .5)}%`;
  $('relegationBar').style.width = `${Math.max(relegation * 100, .5)}%`;
  if (!directNeeded) {
    $('accessDetail').innerHTML = `A campanha já alcançou a referência de <b>${MODEL_LIMITS.direct} pontos</b> usada para o acesso direto.`;
  } else if (direct >= playoffAccess) {
    $('accessDetail').innerHTML = `O cenário mais provável é o <b>acesso direto</b>: faltam ${directNeeded} pontos para a referência de ${MODEL_LIMITS.direct}.`;
  } else {
    $('accessDetail').innerHTML = `O caminho mais viável passa pelo <b>G6 e pelos playoffs</b>; o acesso direto exige ${MODEL_LIMITS.direct} pontos.`;
  }
  if (!playoffNeeded) {
    $('playoffDetail').innerHTML = `A campanha já alcançou a referência de <b>${MODEL_LIMITS.playoff} pontos</b> usada para o G6.`;
  } else if (playoffNeeded > available) {
    $('playoffDetail').innerHTML = `A referência de ${MODEL_LIMITS.playoff} pontos não é mais alcançável: restam <b>${available} pontos</b> em disputa.`;
  } else {
    $('playoffDetail').innerHTML = `São necessários <b>${playoffNeeded} dos ${available} pontos</b> ainda disponíveis.`;
  }
  $('relegationDetail').innerHTML = safetyNeeded
    ? `Com mais <b>${safetyNeeded} pontos</b>, o time chega a ${MODEL_LIMITS.relegation + 1}, acima da faixa conservadora de risco.`
    : `Com <b>${currentPoints} pontos</b>, o time já superou a faixa conservadora de risco (até ${MODEL_LIMITS.relegation} pontos).`;
  $('likelyRange').textContent = `${q10}–${q90} pontos`;
  $('rangeLow').textContent = q10;
  $('rangeMedian').textContent = median;
  $('rangeHigh').textContent = q90;
  $('modelSummary').innerHTML = `Em 80% dos cenários, a campanha termina nessa faixa. O centro da projeção é <b>${median} pontos</b>.`;
}

function longestSequence(predicate) {
  let longest = 0, current = 0;
  matches.forEach(match => {
    current = predicate(match) ? current + 1 : 0;
    longest = Math.max(longest, current);
  });
  return longest;
}

function renderPerformance() {
  // Até duas fileiras de jogos: 14 colunas no mínimo, 19 com a campanha completa.
  $('gameStrip').style.setProperty('--strip-cols', Math.max(14, Math.ceil(matches.length / 2)));
  $('gameStrip').innerHTML = matches.map(match => `<div class="game-tile ${match.result}" title="R${match.round} · ${match.opponent} · ${match.gf} x ${match.ga}">
    <span>R${String(match.round).padStart(2, '0')}</span><strong>${match.result}</strong>
  </div>`).join('');

  const periods = [
    {label: 'Rodadas 1–10', list: matches.slice(0, 10)},
    {label: 'Rodadas 11–20', list: matches.slice(10, 20)},
    {label: `Rodadas 21–${matches.length}`, list: matches.slice(20)}
  ].filter(period => period.list.length);
  const periodData = periods.map(period => ({...period, summary: summarize(period.list)}));
  const best = Math.max(...periodData.map(period => period.summary.efficiency));
  $('periodGrid').innerHTML = periodData.map(period => `<div class="period-card ${period.summary.efficiency === best ? 'best' : ''}">
    <span>${period.label}</span><strong>${pct(period.summary.efficiency)}</strong>
    <div class="period-meter"><i style="width:${period.summary.efficiency}%"></i></div>
    <small>${period.summary.points} pontos · ${period.summary.wins}V ${period.summary.draws}E ${period.summary.losses}D</small>
  </div>`).join('');

  const cleanSheets = matches.filter(match => match.ga === 0).length;
  const recent = summarize(matches.slice(-5));
  const unbeatenRun = longestSequence(match => match.result !== 'D');
  const winningRun = longestSequence(match => match.result === 'V');
  const items = [
    {value: unbeatenRun, unit: unbeatenRun === 1 ? 'jogo' : 'jogos', eyebrow: 'REGULARIDADE', title: 'Maior sequência invicta', note: 'sem derrotas consecutivas', tone: 'red'},
    {value: winningRun, unit: winningRun === 1 ? 'jogo' : 'jogos', eyebrow: 'VITÓRIAS', title: 'Maior sequência de vitórias', note: 'vitórias consecutivas', tone: 'green'},
    {value: cleanSheets, unit: `de ${matches.length} jogos`, eyebrow: 'SOLIDEZ DEFENSIVA', title: 'Jogos sem sofrer gol', note: `${pct(cleanSheets / matches.length * 100)} das partidas`, tone: 'dark'},
    {value: recent.points, unit: `de ${recent.max} pontos`, eyebrow: 'MOMENTO RECENTE', title: 'Últimos 5 jogos', note: `${pct(recent.efficiency)} de aproveitamento`, tone: 'gold'}
  ];
  $('streakGrid').innerHTML = items.map(item => `<div class="streak-item ${item.tone}">
    <span class="streak-eyebrow">${item.eyebrow}</span>
    <div class="streak-value"><b>${item.value}</b><small>${item.unit}</small></div>
    <strong>${item.title}</strong>
    <p>${item.note}</p>
  </div>`).join('');
}

function updateScenario() {
  const target = Number($('targetPoints').value);
  const current = summarize(matches).points;
  const remaining = 38 - matches.length;
  const needed = Math.max(0, target - current);
  $('targetOutput').textContent = target;
  if (!needed) {
    $('scenarioText').innerHTML = `Meta já alcançada: o Vila Nova tem <b>${current} pontos</b>.`;
  } else if (needed > remaining * 3) {
    $('scenarioText').innerHTML = `A meta exige <b>${needed} pontos</b>, acima dos ${remaining * 3} ainda disponíveis.`;
  } else {
    // Menor número de vitórias que fecha a conta; empates completam o que faltar.
    let wins = Math.floor(needed / 3);
    let draws = needed - wins * 3;
    if (wins + draws > remaining) {
      wins += 1;
      draws = 0;
    }
    const parts = [wins && plural(wins, 'vitória', 'vitórias'), draws && plural(draws, 'empate', 'empates')].filter(Boolean);
    const games = remaining === 1 ? 'no jogo restante' : `nos ${remaining} jogos restantes`;
    $('scenarioText').innerHTML = `${needed === 1 ? 'Falta' : 'Faltam'} <b>${plural(needed, 'ponto', 'pontos')}</b>. Um caminho mínimo: <b>${parts.join(' e ')}</b> ${games}.`;
  }
}

function resultPoints(gf, ga) {
  return gf > ga ? 3 : gf === ga ? 1 : 0;
}
function signedNumber(value) {
  return (value > 0 ? '+' : '') + value;
}
function setHalfBalance(id, value) {
  const element = $(id);
  element.textContent = signedNumber(value) + ' saldo';
  element.classList.toggle('positive', value > 0);
  element.classList.toggle('negative', value < 0);
}
function renderHalves(list) {
  const valid = list.filter(m => [m.htGf, m.htGa, m.shGf, m.shGa].every(Number.isFinite));
  if (!valid.length) {
    $('halvesInsight').textContent = 'Os placares de intervalo não estão disponíveis para este recorte.';
    return;
  }
  const totals = valid.reduce((acc, match) => {
    acc.htGf += match.htGf;
    acc.htGa += match.htGa;
    acc.shGf += match.shGf;
    acc.shGa += match.shGa;
    acc.htPoints += resultPoints(match.htGf, match.htGa);
    acc.finalPoints += resultPoints(match.gf, match.ga);
    const before = resultPoints(match.htGf, match.htGa);
    const after = resultPoints(match.gf, match.ga);
    if (after > before) acc.improved += 1;
    if (after < before) acc.worsened += 1;
    return acc;
  }, {htGf: 0, htGa: 0, shGf: 0, shGa: 0, htPoints: 0, finalPoints: 0, improved: 0, worsened: 0});

  const totalScored = totals.htGf + totals.shGf;
  const maxGoals = Math.max(totals.htGf, totals.htGa, totals.shGf, totals.shGa, 1);
  const firstBalance = totals.htGf - totals.htGa;
  const secondBalance = totals.shGf - totals.shGa;
  const pointsSwing = totals.finalPoints - totals.htPoints;
  const unchanged = valid.length - totals.improved - totals.worsened;
  const gameCount = value => value + (value === 1 ? ' jogo' : ' jogos');
  const improvedText = gameCount(totals.improved) + (totals.improved === 1 ? ' melhorou' : ' melhoraram');
  const worsenedText = gameCount(totals.worsened) + (totals.worsened === 1 ? ' piorou' : ' pioraram');
  const unchangedText = gameCount(unchanged) + (unchanged === 1 ? ' manteve' : ' mantiveram');
  const pointsSwingText = signedNumber(pointsSwing) + (Math.abs(pointsSwing) === 1 ? ' ponto' : ' pontos');
  const productive = totals.htGf === totals.shGf ? 'Equilibrado' : totals.htGf > totals.shGf ? '1º tempo' : '2º tempo';
  const vulnerable = totals.htGa === totals.shGa ? 'Equilibrado' : totals.htGa > totals.shGa ? '1º tempo' : '2º tempo';

  $('firstHalfFor').textContent = totals.htGf;
  $('firstHalfAgainst').textContent = totals.htGa;
  $('secondHalfFor').textContent = totals.shGf;
  $('secondHalfAgainst').textContent = totals.shGa;
  $('firstHalfShare').textContent = pct(totalScored ? totals.htGf / totalScored * 100 : 0);
  $('secondHalfShare').textContent = pct(totalScored ? totals.shGf / totalScored * 100 : 0);
  setHalfBalance('firstHalfBalance', firstBalance);
  setHalfBalance('secondHalfBalance', secondBalance);
  $('firstForBar').style.width = (totals.htGf / maxGoals * 100) + '%';
  $('firstAgainstBar').style.width = (totals.htGa / maxGoals * 100) + '%';
  $('secondForBar').style.width = (totals.shGf / maxGoals * 100) + '%';
  $('secondAgainstBar').style.width = (totals.shGa / maxGoals * 100) + '%';
  $('productiveHalf').textContent = productive;
  $('vulnerableHalf').textContent = vulnerable;
  $('improvedResults').innerHTML = '<em class="change-up">' + improvedText + '</em>' +
    '<i>•</i><em class="change-down">' + worsenedText + '</em>';
  $('unchangedResults').textContent = unchangedText + ' o mesmo resultado';
  $('pointsSwing').textContent = pointsSwingText;

  $('halvesInsight').innerHTML = 'Em <b>' + gameCount(totals.improved) + '</b>, o Vila Nova terminou melhor do que estava no intervalo; ' +
    'em <b>' + gameCount(totals.worsened) + '</b>, terminou pior; e em <b>' + gameCount(unchanged) + '</b>, manteve a mesma situação. ' +
    'O saldo dessas mudanças foi de <b>' + pointsSwingText + '</b>.';
}
function renderTable(list) {
  let accumulated = 0;
  const accumulatedByRound = new Map(matches.map(m => [m.round, (accumulated += m.points)]));
  // Busca sem diferenciar acentos: "goias" encontra "Goiás".
  const searchable = (text) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLocaleLowerCase('pt-BR');
  const term = searchable($('matchSearch').value.trim());
  const visible = list.filter(m => searchable(m.opponent).includes(term));
  const resultName = {V: 'Vitória', E: 'Empate', D: 'Derrota'};
  $('matchesBody').innerHTML = visible.map(m => `<tr class="row-${m.result}">
    <td><span class="round-number">${String(m.round).padStart(2,'0')}</span></td><td class="date-cell">${formatDate(m.date)}</td>
    <td><div class="fixture"><span>Vila Nova</span><strong>${m.gf} <i>×</i> ${m.ga}</strong><span>${m.opponent}</span></div></td>
    <td><span class="venue-tag ${m.venue.toLowerCase()}">${m.venue}</span></td>
    <td><div class="result-cell"><span class="badge ${m.result}">${m.result}</span><b>${resultName[m.result]}</b></div></td>
    <td><span class="points-pill ${m.result}">+${m.points}</span></td>
    <td><div class="accumulated"><b>${accumulatedByRound.get(m.round)}</b><span>pts</span></div></td>
  </tr>`).join('');
  $('emptyState').hidden = visible.length > 0;
}

function applyFilter(filter) {
  activeFilter = filter;
  const list = filter === 'Todos' ? matches : matches.filter(m => m.venue === filter);
  renderSummary(list);
  renderForm(list);
  renderHalves(list);
  renderTable(list);
}

document.querySelectorAll('#venueFilter button').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('#venueFilter button').forEach(b => b.classList.remove('active'));
  button.classList.add('active');
  applyFilter(button.dataset.filter);
}));
$('targetPoints').addEventListener('input', updateScenario);
$('matchSearch').addEventListener('input', () => applyFilter(activeFilter));

function parseCsv(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (char === '"' && quoted && text[i + 1] === '"') { field += '"'; i++; }
    else if (char === '"') quoted = !quoted;
    else if (char === ',' && !quoted) { row.push(field); field = ''; }
    else if ((char === '\n' || char === '\r') && !quoted) {
      if (char === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.some(value => value !== '')) rows.push(row);
      row = [];
    } else field += char;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const headers = rows.shift().map(header => header.trim());
  return rows.map(values => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ''])));
}

async function loadCsv() {
  try {
    let csvText = window.__VILANOVA_CSV__;
    if (!csvText) {
      const response = await fetch('vila_nova_serie_b_2026_todos_jogos.csv', {cache: 'no-store'});
      if (!response.ok) return;
      csvText = await response.text();
    }
    const rows = parseCsv(csvText);
    const records = rows.filter(row => row.status === 'finished' && ['V','E','D'].includes(row.resultado));
    if (!records.length) return;
    // Campo vazio vira NaN (e não 0), para a análise por tempo ignorar placares ausentes.
    const toNumber = (value) => value === '' ? NaN : Number(value);
    matches = records.map((row, index) => ({
      round: index + 1,
      date: row.data,
      opponent: row.adversario,
      venue: row.mando,
      gf: Number(row.gols_vila_nova),
      ga: Number(row.gols_adversario),
      htGf: toNumber(row.gols_1t_vila_nova),
      htGa: toNumber(row.gols_1t_adversario),
      shGf: toNumber(row.gols_2t_vila_nova),
      shGa: toNumber(row.gols_2t_adversario),
      result: row.resultado,
      points: row.resultado === 'V' ? 3 : row.resultado === 'E' ? 1 : 0
    }));
    upcoming = rows
      .filter(row => ['scheduled', 'postponed'].includes(row.status))
      .map(row => ({date: row.data, opponent: row.adversario, venue: row.mando}));
  } catch (_) {
    // Em file://, o navegador bloqueia fetch local; os dados incorporados acima mantêm o painel funcional.
  }
}

// Finanças: dados de financas_2025.js, gerados por extrair_financas.py (valores em R$ mil).
const FIN = window.VILA_NOVA_FINANCAS;
const millions = (value) => oneDecimal(Math.abs(value) / 1000);
const money = (value) => Math.abs(value) < 1000 ? `R$ ${Math.abs(value).toLocaleString('pt-BR')} mil` : `R$ ${millions(value)} mi`;
const minus = (value) => value < 0 ? '−' : '';
const listJoin = (items) => items.length > 1 ? `${items.slice(0, -1).join(', ')} e ${items.at(-1)}` : items.join('');

function variation(item) {
  return item.anterior ? (Math.abs(item.atual) - Math.abs(item.anterior)) / Math.abs(item.anterior) * 100 : null;
}

function changeTone(change, goodWhenUp) {
  if (change === null || Math.abs(change) < .05 || goodWhenUp === null) return 'neutral';
  return (change > 0) === goodWhenUp ? 'good' : 'bad';
}

function changeLabel(change) {
  return change === null ? 'novo' : `${change > 0 ? '▲' : '▼'} ${oneDecimal(Math.abs(change))}%`;
}

function pairRows(items, goodWhenUp, total) {
  const max = Math.max(...items.flatMap(item => [Math.abs(item.atual), Math.abs(item.anterior)]));
  return items.map(item => {
    const change = variation(item);
    const share = total ? `${oneDecimal(Math.abs(item.atual) / total * 100)}% do total · ` : '';
    return `<div class="pair-row" title="${item.nome}: ${money(item.atual)} em ${FIN.exercicio} e ${money(item.anterior)} em ${FIN.comparativo}">
      <div class="pair-label"><b>${item.nome}</b><small>${share}${item.detalhe || ''}</small></div>
      <div class="pair-bars">
        <div class="pair-bar current"><i style="width:${Math.abs(item.atual) / max * 80}%"></i><span>${millions(item.atual)}</span></div>
        <div class="pair-bar previous"><i style="width:${Math.abs(item.anterior) / max * 80}%"></i><span>${millions(item.anterior)}</span></div>
      </div>
      <em class="pair-change ${changeTone(change, goodWhenUp)}">${changeLabel(change)}</em>
    </div>`;
  }).join('');
}

function factCards(items) {
  return items.map(item => `<div><span>${item.label}</span><b>${item.value}</b><small>${item.note}</small></div>`).join('');
}

function renderFinanceKpis() {
  const {faturamento, venda_atletas: sales, resultado, divida, elenco} = FIN;
  const mutuos = divida.itens.find(item => item.nome.startsWith('Mútuos'));
  const deficitNow = resultado.atual < 0;
  const resultChange = variation(resultado);
  const resultDelta = deficitNow && resultado.anterior < 0
    ? {tone: resultChange < 0 ? 'good' : 'bad', text: `Déficit ${oneDecimal(Math.abs(resultChange))}% ${resultChange < 0 ? 'menor' : 'maior'}`}
    : {tone: deficitNow ? 'bad' : 'good', text: deficitNow ? 'Voltou ao déficit' : 'Superávit no ano'};
  const kpis = [
    {
      label: 'Faturamento total', badge: 'RECEITAS', value: money(faturamento.atual),
      delta: {tone: changeTone(variation(faturamento), true), text: `${changeLabel(variation(faturamento))} vs. ${FIN.comparativo}`},
      note: `Receitas de ${money(faturamento.atual - sales.atual)} + venda de atletas de ${money(sales.atual)}`
    },
    {
      label: 'Resultado do exercício', badge: 'DRE', value: `${minus(resultado.atual)}${money(resultado.atual)}`,
      delta: resultDelta,
      note: `Em ${FIN.comparativo}: ${resultado.anterior < 0 ? 'déficit' : 'superávit'} de ${money(resultado.anterior)}`
    },
    {
      label: 'Dívida total', badge: 'BALANÇO', value: money(divida.total.atual),
      delta: {tone: changeTone(variation(divida.total), false), text: `${changeLabel(variation(divida.total))} vs. ${FIN.comparativo}`},
      note: `${oneDecimal(mutuos.atual / divida.total.atual * 100)}% em mútuos com conselheiros`
    },
    {
      label: 'Investimento no elenco', badge: 'ATLETAS', value: money(elenco.adicoes.atual),
      delta: {tone: 'neutral', text: `${changeLabel(variation(elenco.adicoes))} vs. ${FIN.comparativo}`},
      note: `Direitos de atletas no balanço: de ${money(elenco.saldo_inicial.atual)} para ${money(elenco.saldo_final.atual)}`
    }
  ];
  $('financeKpis').innerHTML = kpis.map(kpi => `<article class="kpi">
    <div class="kpi-top"><span>${kpi.label}</span><span class="kpi-icon">${kpi.badge}</span></div>
    <strong>${kpi.value}</strong>
    <small class="finance-delta ${kpi.delta.tone}">${kpi.delta.text}</small>
    <small>${kpi.note}</small>
  </article>`).join('');
}

function renderWaterfall() {
  const dre = Object.fromEntries(FIN.dre.map(item => [item.nome, item.atual]));
  const result = dre['Resultado do exercício'];
  const steps = [
    ['Receita líquida', dre['Receita operacional líquida'], true],
    ['Custo do futebol', dre['Custo das atividades esportivas']],
    ['Pessoal', dre['Despesas com pessoal']],
    ['Despesas gerais', dre['Despesas gerais']],
    ['Outras receitas', dre['Outras receitas líquidas']],
    ['Resultado financeiro', dre['Resultado financeiro']],
    [result < 0 ? 'Déficit' : 'Superávit', result, true]
  ];
  let running = 0;
  const bars = steps.map(([label, value, total], index) => {
    const start = total ? 0 : running;
    running = total ? value : running + value;
    const kind = index === steps.length - 1 ? 'result' : value >= 0 ? 'in' : 'out';
    return {label, value, total, end: running, kind, low: Math.min(start, running), high: Math.max(start, running)};
  });
  const low = Math.min(0, ...bars.map(bar => bar.low));
  const high = Math.max(0, ...bars.map(bar => bar.high));
  const pad = (high - low) * .14;
  const y = (value) => (value - low + pad) / (high - low + pad * 2) * 100;
  const chart = $('dreWaterfall');
  chart.style.setProperty('--steps', bars.length);
  chart.innerHTML = `<div class="wf-plot">
      <i class="wf-zero" style="bottom:${y(0)}%"></i>
      ${bars.map((bar, index) => {
        const text = bar.total ? `${minus(bar.value)}${millions(bar.value)}` : `${bar.value < 0 ? '−' : '+'}${millions(bar.value)}`;
        const place = bar.value < 0 ? `top:${100 - y(bar.low)}%` : `bottom:${y(bar.high)}%`;
        return `<div class="wf-bar ${bar.kind}" style="--i:${index}; bottom:${y(bar.low)}%; height:${y(bar.high) - y(bar.low)}%" title="${bar.label}: ${bar.total ? minus(bar.value) : bar.value < 0 ? '−' : '+'}${money(bar.value)} · acumulado ${minus(bar.end)}${money(bar.end)}"></div>
          <span class="wf-value" style="--i:${index}; ${place}">${text}</span>`;
      }).join('')}
    </div>
    <div class="wf-labels">${bars.map(bar => `<span>${bar.label}</span>`).join('')}</div>`;

  $('dreTable').innerHTML = FIN.dre.map(item => {
    const diff = item.atual - item.anterior;
    return `<tr class="${item.tipo || ''}"><td>${item.nome}</td><td>${minus(item.atual)}${millions(item.atual)}</td><td>${minus(item.anterior)}${millions(item.anterior)}</td><td>${diff > 0 ? '+' : diff < 0 ? '−' : ''}${millions(diff)}</td></tr>`;
  }).join('');
}

function renderCashFlow() {
  const {atividades, inicial, final, aquisicao_atletas: players, captacao} = FIN.caixa;
  const max = Math.max(...atividades.flatMap(item => [Math.abs(item.atual), Math.abs(item.anterior)]));
  const track = (value, cls) => {
    const size = Math.abs(value) / max * 32;
    const bar = value >= 0 ? `left:50%; width:${size}%` : `left:${50 - size}%; width:${size}%`;
    const label = value >= 0 ? `left:calc(${50 + size}% + 6px)` : `right:calc(${50 + size}% + 6px)`;
    return `<div class="cash-track ${cls}"><i class="${value >= 0 ? 'pos' : 'neg'}" style="${bar}"></i><span style="${label}">${value < 0 ? '−' : '+'}${millions(value)}</span></div>`;
  };
  $('cashFlow').innerHTML = atividades.map(item => `<div class="cash-row" title="${item.nome}: ${minus(item.atual)}${money(item.atual)} em ${FIN.exercicio} e ${minus(item.anterior)}${money(item.anterior)} em ${FIN.comparativo}">
      <div class="pair-label"><b>${item.nome}</b><small>${item.detalhe}</small></div>
      <div class="cash-bars">${track(item.atual, 'current')}${track(item.anterior, 'previous')}</div>
    </div>`).join('');
  $('cashFacts').innerHTML = factCards([
    {label: 'Caixa no fim do ano', value: money(final.atual), note: `${money(inicial.atual)} no fim de ${FIN.comparativo}`},
    {label: 'Compra de direitos', value: money(players.atual), note: `${money(players.anterior)} em ${FIN.comparativo}`},
    {label: 'Empréstimos captados', value: money(captacao.atual), note: `${money(captacao.anterior)} em ${FIN.comparativo}`}
  ]);
}

function renderSsf() {
  $('ssfList').innerHTML = FIN.ssf.map(item => `<div class="ssf-row ${item.conforme ? 'ok' : 'fail'}">
      <i aria-hidden="true">${item.conforme ? '✓' : '!'}</i>
      <div><b>${item.indicador}</b><small>Exigência na Série B: ${item.limite}</small></div>
      <div class="ssf-result"><strong>${item.apurado}</strong><span>${item.conforme ? 'Conforme' : 'Não conforme'}</span></div>
    </div>`).join('');
  const limits = FIN.ssf_limites.map((item, index, all) => `${item.limite}% ${index === all.length - 1 ? 'a partir de' : 'em'} ${item.ano}`);
  const debtIssue = FIN.ssf.some(item => /Endividamento/.test(item.indicador) && !item.conforme);
  $('ssfNote').textContent = `O limite do endividamento de curto prazo cai para ${listJoin(limits)}.` +
    (debtIssue ? ' Segundo o clube, o desenquadramento vem de dívidas tributárias que foram para a Dívida Ativa após a perda do parcelamento Profut; a gestão negocia o reparcelamento.' : '');
}

function renderFinance() {
  if (!FIN) {
    $('financas').hidden = true;
    document.querySelector('nav a[href="#financas"]').hidden = true;
    return;
  }
  document.querySelectorAll('.year-current').forEach(element => { element.textContent = FIN.exercicio; });
  document.querySelectorAll('.year-previous').forEach(element => { element.textContent = FIN.comparativo; });
  renderFinanceKpis();

  const highlight = (name) => FIN.destaques_receita.find(item => item.nome === name);
  const ticket = highlight('Bilheteria');
  const lfu = highlight('Adesão à LFU');
  $('revenueBars').innerHTML = pairRows(FIN.receitas, true, FIN.faturamento.atual);
  $('revenueFacts').innerHTML = factCards([
    {label: 'Receita recorrente', value: money(FIN.receita_recorrente.atual), note: `${changeLabel(variation(FIN.receita_recorrente))} sem a adesão à LFU`},
    {label: 'Bilheteria', value: money(ticket.atual), note: `${changeLabel(variation(ticket))} vs. ${FIN.comparativo}`},
    {label: 'Adesão à LFU', value: money(lfu.atual), note: `${changeLabel(variation(lfu))} vs. ${FIN.comparativo}`}
  ]);

  const costTotal = FIN.custos.reduce((sum, item) => sum + Math.abs(item.atual), 0);
  $('costBars').innerHTML = pairRows(FIN.custos, false, costTotal);
  const footballItems = [...FIN.custo_futebol].sort((a, b) => Math.abs(b.atual) - Math.abs(a.atual));
  const footballMax = Math.abs(footballItems[0].atual);
  $('footballCostBars').innerHTML = footballItems.map(item => `<div class="mini-bar" title="${item.nome}: ${money(item.atual)} em ${FIN.exercicio} e ${money(item.anterior)} em ${FIN.comparativo}">
      <span>${item.nome}</span>
      <div><i style="width:${Math.abs(item.atual) / footballMax * 78}%"></i><b>${millions(item.atual)}</b></div>
    </div>`).join('');

  renderWaterfall();

  const {balanco} = FIN;
  $('debtBars').innerHTML = pairRows(FIN.divida.itens, false, FIN.divida.total.atual);
  $('balanceFacts').innerHTML = factCards([
    {label: 'Patrimônio social', value: `${minus(balanco.patrimonio_social.atual)}${money(balanco.patrimonio_social.atual)}`, note: balanco.patrimonio_social.atual < 0 ? 'Passivos maiores que os ativos' : 'Ativos maiores que os passivos'},
    {label: 'Empréstimos bancários', value: money(balanco.emprestimos.atual), note: `${money(balanco.emprestimos.anterior)} em ${FIN.comparativo}`},
    {label: 'Subvenções recebidas', value: money(balanco.subvencoes.atual), note: 'Ficam fora da conta da dívida'}
  ]);

  renderCashFlow();
  renderSsf();

  const football = FIN.custos.find(item => item.nome === 'Custo do futebol');
  const driver = [...FIN.custo_futebol].sort((a, b) => (Math.abs(b.atual) - Math.abs(b.anterior)) - (Math.abs(a.atual) - Math.abs(a.anterior)))[0];
  const recurring = variation(FIN.receita_recorrente);
  const footballChange = variation(football);
  const {resultado} = FIN;
  const deficitShrank = resultado.atual < 0 && resultado.anterior < 0 && Math.abs(resultado.atual) < Math.abs(resultado.anterior);
  const outcome = deficitShrank
    ? `O déficit caiu de ${money(resultado.anterior)} para ${money(resultado.atual)} graças à venda de atletas (${money(FIN.venda_atletas.atual)})` +
      (FIN.waiver_mi ? ` e à dispensa dos juros dos mútuos, que evitou cerca de R$ ${FIN.waiver_mi.toLocaleString('pt-BR')} mi em encargos.` : '.')
    : `O exercício terminou com ${resultado.atual < 0 ? 'déficit' : 'superávit'} de ${money(resultado.atual)}.`;
  $('financeInsight').innerHTML = `A receita recorrente (sem a LFU) ${recurring >= 0 ? 'cresceu' : 'caiu'} <b>${oneDecimal(Math.abs(recurring))}%</b>, ` +
    `enquanto o custo do futebol ${footballChange >= 0 ? 'subiu' : 'caiu'} <b>${oneDecimal(Math.abs(footballChange))}%</b> ` +
    `(maior aumento: ${driver.nome.toLocaleLowerCase('pt-BR')}, de ${money(driver.anterior)} para ${money(driver.atual)}). ${outcome}`;
  $('financeSource').textContent = `Fonte: ${FIN.fonte}, auditadas. Números extraídos do PDF por extrair_financas.py. A dívida é o passivo total sem as subvenções recebidas, critério do relatório da administração.`;
}

function renderAll() {
  applyFilter('Todos');
  renderChart(matches);
  renderVenue();
  renderProjection();
  renderProbabilities();
  renderPerformance();
  renderFinance();
}

$('modelInfoButton').addEventListener('click', () => {
  const explanation = $('modelExplanation');
  explanation.hidden = !explanation.hidden;
  $('modelInfoButton').textContent = explanation.hidden ? 'Como calculamos?' : 'Ocultar metodologia';
});

loadCsv().finally(renderAll);
