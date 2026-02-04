const POKER_MATH_MODULES = [
  { id: "probability", title: "Probability & Counting" },
  { id: "outs", title: "Outs & Equity" },
  { id: "pot_odds", title: "Pot Odds & Implied Odds" },
  { id: "ev", title: "EV & Betting Math" },
  { id: "mdf", title: "Defense Frequencies (MDF)" },
  { id: "rake", title: "Cash Game Rake Impact" }
];

const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];

function makeChoices(rng, correct, spread, decimals) {
  const choices = new Set();
  choices.add(correct);
  while (choices.size < 4) {
    const delta = (rng() * spread * 2) - spread;
    let val = correct + delta;
    if (decimals === 0) {
      val = Math.round(val);
    } else {
      const factor = Math.pow(10, decimals);
      val = Math.round(val * factor) / factor;
    }
    if (val >= 0) {
      choices.add(val);
    }
  }
  return Array.from(choices).sort(() => rng() - 0.5);
}

function comboCountForHand(hand) {
  if (hand.endsWith("s")) return 4;
  if (hand.endsWith("o")) return 12;
  return 6;
}

function rangeCount(rangeText) {
  const tokens = rangeText.split(",").map(t => t.trim()).filter(Boolean);
  let total = 0;
  for (const token of tokens) {
    if (/^\d{2}\+$/.test(token)) {
      const pairRank = token[0];
      const idx = RANKS.indexOf(pairRank);
      for (let i = idx; i >= 0; i--) {
        total += 6;
      }
      continue;
    }
    if (/^[AKQJT98765432][AKQJT98765432]s\+$/.test(token)) {
      const high = token[0];
      const low = token[1];
      const highIdx = RANKS.indexOf(high);
      const lowIdx = RANKS.indexOf(low);
      for (let i = lowIdx; i >= highIdx + 1; i--) {
        total += 4;
      }
      continue;
    }
    if (/^[AKQJT98765432][AKQJT98765432]o$/.test(token) ||
        /^[AKQJT98765432][AKQJT98765432]s$/.test(token)) {
      total += comboCountForHand(token);
      continue;
    }
  }
  return total;
}

const QUESTION_TEMPLATES = [
  // Probability & Counting (6)
  {
    id: "prob-complement",
    moduleId: "probability",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const p = randInt(rng, 15, 65);
      const answer = 100 - p;
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `If you have a ${p}% chance to hit on the next card, what is the % chance to miss?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Complement rule: <span class="formula">1 - p</span> = ${answer}%.`
      };
    }
  },
  {
    id: "prob-conditional-removal",
    moduleId: "probability",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const outs = randInt(rng, 4, 15);
      const unseen = 47;
      const answer = roundPct((outs / unseen) * 100);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `You have ${outs} outs on the turn with ${unseen} unseen cards. What is your exact % to hit on the turn?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Conditional probability: <span class="formula">${outs}/${unseen}</span> = ${answer}%.`
      };
    }
  },
  {
    id: "prob-ncr",
    moduleId: "probability",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const n = randInt(rng, 8, 12);
      const r = randInt(rng, 2, 4);
      const answer = nCr(n, r);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Compute combinations: C(${n}, ${r}).`,
        answer,
        tolerance: 0.01,
        explanationHtml: `Use <span class="formula">nCr = n!/(r!(n-r)!)</span> → ${answer}.`
      };
    }
  },
  {
    id: "prob-starting-combos",
    moduleId: "probability",
    difficulty: "easy",
    format: "multiple",
    generate(rng) {
      const hands = ["AKo", "A5s", "77", "KQs", "JTo"];
      const hand = choice(rng, hands);
      const answer = comboCountForHand(hand);
      const choices = makeChoices(rng, answer, 6, 0);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `How many starting-hand combos are there for <strong>${hand}</strong>?`,
        choices,
        answer,
        explanationHtml: `Pairs = 6 combos, suited = 4 combos, offsuit = 12 combos.`
      };
    }
  },
  {
    id: "prob-range-count",
    moduleId: "probability",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const range = choice(rng, ["ATs+, KQs, 99+", "A5s+, 88+", "KQs, QJs, 99+"]);
      const answer = rangeCount(range);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `How many total combos are in the range <strong>${range}</strong>?`,
        answer,
        tolerance: 0.01,
        explanationHtml: `Sum combos per token. Pairs = 6, suited = 4. Total = ${answer}.`
      };
    }
  },
  {
    id: "prob-board-combos",
    moduleId: "probability",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const unseen = choice(rng, [45, 46, 47]);
      const answer = nCr(unseen, 2);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `How many 2-card combinations are possible from ${unseen} unseen cards?`,
        answer,
        tolerance: 0.01,
        explanationHtml: `<span class="formula">C(${unseen}, 2)</span> = ${answer}.`
      };
    }
  },

  // Outs & Equity (6)
  {
    id: "outs-rule2",
    moduleId: "outs",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const outs = randInt(rng, 4, 15);
      const answer = roundPct(outs * 2);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Using the Rule of 2, what % to hit by the turn with ${outs} outs?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Rule of 2: <span class="formula">outs × 2</span> = ${answer}%.`
      };
    }
  },
  {
    id: "outs-rule4",
    moduleId: "outs",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const outs = randInt(rng, 4, 15);
      const answer = roundPct(outs * 4);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Using the Rule of 4, what % to hit by the river with ${outs} outs?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Rule of 4: <span class="formula">outs × 4</span> = ${answer}%.`
      };
    }
  },
  {
    id: "outs-exact-river",
    moduleId: "outs",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const outs = randInt(rng, 6, 15);
      const unseen = 47;
      const answer = roundPct(drawByRiverExact(outs, unseen));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Exact chance to hit by the river with ${outs} outs (U=${unseen})?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Exact: <span class="formula">1 - ((U-N)/U) × ((U-1-N)/(U-1))</span> = ${answer}%.`
      };
    }
  },
  {
    id: "outs-exact-turn",
    moduleId: "outs",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const outs = randInt(rng, 4, 12);
      const unseen = 47;
      const answer = roundPct(drawByTurnExact(outs, unseen));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Exact chance to hit on the turn with ${outs} outs (U=${unseen})?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Exact: <span class="formula">outs / U</span> = ${answer}%.`
      };
    }
  },
  {
    id: "outs-clean-dirty",
    moduleId: "outs",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const total = randInt(rng, 8, 15);
      const dirty = randInt(rng, 2, 5);
      const answer = total - dirty;
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `You have ${total} outs but ${dirty} are dirty. How many clean outs?`,
        answer,
        tolerance: 0.01,
        explanationHtml: `Clean outs = ${total} - ${dirty} = ${answer}.`
      };
    }
  },
  {
    id: "outs-backdoor",
    moduleId: "outs",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const unseen = 47;
      const answer = roundPct((10 / unseen) * (9 / (unseen - 1)) * 100);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Backdoor flush (you hold 2 suited, flop has 1 of suit). Exact % to complete by river?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Need two suited: <span class="formula">(10/47) × (9/46)</span> = ${answer}%.`
      };
    }
  },

  // Pot Odds & Implied Odds (6)
  {
    id: "pot-req-equity",
    moduleId: "pot_odds",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 6, 20);
      const call = randInt(rng, 2, 8);
      const answer = roundPct(potOddsRequiredEquity(pot, call));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Pot is ${pot} BB and you must call ${call} BB. Required equity %?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `<span class="formula">call / (pot + call)</span> = ${answer}%.`
      };
    }
  },
  {
    id: "pot-multiway",
    moduleId: "pot_odds",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 8, 20);
      const call = randInt(rng, 2, 8);
      const extra = randInt(rng, 2, 6);
      const answer = roundPct(potOddsRequiredEquity(pot + extra, call));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Pot is ${pot} BB, another player calls ${extra} BB, you must call ${call} BB. Required equity %?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Multiway: pot = ${pot + extra}. Required equity = ${answer}%.`
      };
    }
  },
  {
    id: "pot-implied",
    moduleId: "pot_odds",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 6, 18);
      const call = randInt(rng, 3, 8);
      const equity = randInt(rng, 20, 35);
      const requiredTotal = call / (equity / 100);
      const extraNeeded = Math.max(0, roundBB(requiredTotal - (pot + call)));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Pot is ${pot} BB, call ${call} BB with ${equity}% equity. How much extra must you win on average to break even?`,
        answer: extraNeeded,
        tolerance: 0.05,
        explanationHtml: `Break-even: <span class="formula">equity × (pot + call + X) = call</span>. X = ${extraNeeded} BB.`
      };
    }
  },
  {
    id: "pot-reverse-implied",
    moduleId: "pot_odds",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 6, 18);
      const call = randInt(rng, 3, 8);
      const reverse = randInt(rng, 4, 10);
      const answer = roundPct(((call + reverse) / (pot + call + reverse)) * 100);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `You call ${call} BB into a ${pot} BB pot, but expect to lose ${reverse} BB extra when behind. Required equity %?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Adjusted: <span class="formula">(call + reverse) / (pot + call + reverse)</span> = ${answer}%.`
      };
    }
  },
  {
    id: "pot-spr",
    moduleId: "pot_odds",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const stack = randInt(rng, 40, 120);
      const pot = randInt(rng, 8, 30);
      const answer = roundBB(stack / pot);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Effective stack ${stack} BB and pot ${pot} BB. What is SPR?`,
        answer,
        tolerance: 0.05,
        explanationHtml: `<span class="formula">SPR = stack / pot</span> = ${answer}.`
      };
    }
  },
  {
    id: "pot-odds-ratio",
    moduleId: "pot_odds",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 6, 16);
      const call = randInt(rng, 2, 6);
      const answer = roundPct(potOddsRequiredEquity(pot, call));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Pot ${pot} BB, call ${call} BB. Required equity % (show percent only).`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Required equity = ${answer}%.`
      };
    }
  },

  // EV & Betting Math (6)
  {
    id: "ev-call",
    moduleId: "ev",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 8, 20);
      const call = randInt(rng, 2, 8);
      const equity = randInt(rng, 25, 55);
      const answer = roundBB(evCall(pot, call, equity));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `EV of calling ${call} BB into ${pot} BB pot with ${equity}% equity?`,
        answer,
        tolerance: 0.05,
        explanationHtml: `<span class="formula">EV = eq × (pot + call) - (1-eq) × call</span> = ${answer} BB.`
      };
    }
  },
  {
    id: "ev-bet",
    moduleId: "ev",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 8, 20);
      const bet = randInt(rng, 4, 10);
      const fold = randInt(rng, 20, 60);
      const equity = randInt(rng, 25, 55);
      const answer = roundBB(evBet(pot, bet, fold, equity));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Bet ${bet} BB into ${pot} BB. Fold% = ${fold}%, equity when called = ${equity}%. EV?`,
        answer,
        tolerance: 0.05,
        explanationHtml: `<span class="formula">EV = f×pot + (1-f)×(eq×(pot+bet) - (1-eq)×bet)</span> = ${answer} BB.`
      };
    }
  },
  {
    id: "ev-bluff-break-even",
    moduleId: "ev",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 6, 20);
      const bet = randInt(rng, 4, 12);
      const answer = roundPct(bluffBreakEvenFold(pot, bet));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `You bluff ${bet} BB into ${pot} BB. Break-even fold %?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `<span class="formula">risk / (risk + reward)</span> = ${answer}%.`
      };
    }
  },
  {
    id: "ev-bluffcatch",
    moduleId: "ev",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 6, 20);
      const bet = randInt(rng, 4, 12);
      const answer = roundPct((bet / (pot + bet)) * 100);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Facing a ${bet} BB bet into ${pot} BB. Required win rate to call?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Same as pot odds: ${answer}%.`
      };
    }
  },
  {
    id: "ev-value-threshold",
    moduleId: "ev",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 8, 20);
      const bet = randInt(rng, 4, 10);
      const answer = roundPct((bet / (pot + 2 * bet)) * 100);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `If you bet ${bet} BB into ${pot} BB and always get called, what equity % makes the bet break-even?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Break-even when called: <span class="formula">bet / (pot + 2×bet)</span> = ${answer}%.`
      };
    }
  },
  {
    id: "ev-call-compare",
    moduleId: "ev",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 10, 24);
      const call = randInt(rng, 4, 10);
      const equity = randInt(rng, 30, 60);
      const answer = roundBB(evCall(pot, call, equity));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `EV of calling ${call} BB into ${pot} BB with ${equity}% equity?`,
        answer,
        tolerance: 0.05,
        explanationHtml: `Use call EV formula → ${answer} BB.`
      };
    }
  },

  // MDF (3)
  {
    id: "mdf-basic",
    moduleId: "mdf",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 10, 24);
      const bet = randInt(rng, 4, 12);
      const answer = roundPct(mdf(pot, bet));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Facing a ${bet} BB bet into ${pot} BB, what is MDF %?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `<span class="formula">MDF = pot / (pot + bet)</span> = ${answer}%.`
      };
    }
  },
  {
    id: "mdf-halfpot",
    moduleId: "mdf",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 10, 24);
      const bet = Math.round(pot * 0.5);
      const answer = roundPct(mdf(pot, bet));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `MDF vs half-pot bet: pot ${pot} BB, bet ${bet} BB.`,
        answer,
        tolerance: 0.5,
        explanationHtml: `MDF = ${answer}%.`
      };
    }
  },
  {
    id: "mdf-twothirds",
    moduleId: "mdf",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 12, 24);
      const bet = Math.round(pot * 0.66);
      const answer = roundPct(mdf(pot, bet));
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `MDF vs 2/3 pot bet: pot ${pot} BB, bet ${bet} BB.`,
        answer,
        tolerance: 0.5,
        explanationHtml: `MDF = ${answer}%.`
      };
    }
  },

  // Rake (3)
  {
    id: "rake-amount",
    moduleId: "rake",
    difficulty: "easy",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 20, 60);
      const rakePct = choice(rng, [5, 4, 3]);
      const cap = choice(rng, [2, 3]);
      const rake = applyRake(pot, rakePct, cap);
      const answer = roundBB(rake);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Pot is ${pot} BB. Rake ${rakePct}% with cap ${cap} BB. Rake taken?`,
        answer,
        tolerance: 0.05,
        explanationHtml: `Rake = min(pot × ${rakePct}%, cap ${cap}) = ${answer} BB.`
      };
    }
  },
  {
    id: "rake-breakeven",
    moduleId: "rake",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 12, 30);
      const call = randInt(rng, 4, 10);
      const rakePct = 5;
      const cap = 2;
      const totalPot = pot + call;
      const rake = applyRake(totalPot, rakePct, cap);
      const adjustedPot = totalPot - rake;
      const answer = roundPct((call / adjustedPot) * 100);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Pot ${pot} BB, call ${call} BB. Rake ${rakePct}% cap ${cap} BB. Required equity % after rake?`,
        answer,
        tolerance: 0.5,
        explanationHtml: `Adjusted pot = ${adjustedPot.toFixed(2)}. Required equity = ${answer}%.`
      };
    }
  },
  {
    id: "rake-ev-call",
    moduleId: "rake",
    difficulty: "medium",
    format: "numeric",
    generate(rng) {
      const pot = randInt(rng, 12, 30);
      const call = randInt(rng, 4, 10);
      const equity = randInt(rng, 30, 55);
      const rakePct = 5;
      const cap = 2;
      const totalPot = pot + call;
      const rake = applyRake(totalPot, rakePct, cap);
      const adjustedPot = totalPot - rake;
      const answer = roundBB((equity / 100) * adjustedPot - (1 - equity / 100) * call);
      return {
        id: this.id,
        moduleId: this.moduleId,
        difficulty: this.difficulty,
        format: this.format,
        promptHtml: `Pot ${pot} BB, call ${call} BB, equity ${equity}%. Rake ${rakePct}% cap ${cap} BB. EV of call?`,
        answer,
        tolerance: 0.05,
        explanationHtml: `EV = eq × (pot+call-rake) - (1-eq)×call = ${answer} BB.`
      };
    }
  }
];

function getTemplatesForModule(moduleId) {
  return QUESTION_TEMPLATES.filter(t => t.moduleId === moduleId);
}

function getAllTemplates() {
  return QUESTION_TEMPLATES.slice();
}
