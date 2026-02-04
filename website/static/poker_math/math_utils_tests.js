(function() {
  function assertEqual(label, actual, expected) {
    if (actual !== expected) {
      console.error(`[FAIL] ${label}: expected ${expected}, got ${actual}`);
    } else {
      console.log(`[PASS] ${label}`);
    }
  }

  assertEqual("nCr 5C2", nCr(5, 2), 10);
  assertEqual("pot odds 4/10", roundPct(potOddsRequiredEquity(10, 4)), 28.6);
  assertEqual("bluff BE 10/5", roundPct(bluffBreakEvenFold(10, 5)), 33.3);
  assertEqual("mdf 10/5", roundPct(mdf(10, 5)), 66.7);
})();
