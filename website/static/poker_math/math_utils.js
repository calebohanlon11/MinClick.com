function mulberry32(seed) {
  var t = seed >>> 0;
  return function() {
    t += 0x6D2B79F5;
    var r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function randInt(rng, min, max) {
  return Math.floor(rng() * (max - min + 1)) + min;
}

function choice(rng, arr) {
  return arr[randInt(rng, 0, arr.length - 1)];
}

function nCr(n, r) {
  if (r > n || r < 0) return 0;
  r = Math.min(r, n - r);
  var num = 1;
  var den = 1;
  for (var i = 1; i <= r; i++) {
    num *= (n - r + i);
    den *= i;
  }
  return Math.round(num / den);
}

function potOddsRequiredEquity(pot, call) {
  return (call / (pot + call)) * 100;
}

function bluffBreakEvenFold(pot, bet) {
  return (bet / (bet + pot)) * 100;
}

function mdf(pot, bet) {
  return (pot / (pot + bet)) * 100;
}

function drawByRiverExact(outs, unseen) {
  var pMiss1 = (unseen - outs) / unseen;
  var pMiss2 = (unseen - 1 - outs) / (unseen - 1);
  return (1 - (pMiss1 * pMiss2)) * 100;
}

function drawByTurnExact(outs, unseen) {
  return (outs / unseen) * 100;
}

function evCall(pot, call, equityPct) {
  var equity = equityPct / 100;
  return equity * (pot + call) - (1 - equity) * call;
}

function evBet(pot, bet, foldPct, equityWhenCalledPct) {
  var fold = foldPct / 100;
  var equity = equityWhenCalledPct / 100;
  return fold * pot + (1 - fold) * (equity * (pot + bet) - (1 - equity) * bet);
}

function applyRake(pot, rakePct, cap) {
  var rake = pot * (rakePct / 100);
  if (cap !== null && cap !== undefined) {
    rake = Math.min(rake, cap);
  }
  return rake;
}

function roundPct(value) {
  return Math.round(value * 10) / 10;
}

function roundBB(value) {
  return Math.round(value * 100) / 100;
}
