import re
import pandas as pd
from .PokerStarsHandProcessor import PokerStarsHandProcessor


class GGPokerHandProcessor(PokerStarsHandProcessor):
    """Processor for GGPoker cash-game hand histories (6-max).

    GGPoker's format is nearly identical to PokerStars with a few differences:
      - Hand delimiter: "Poker Hand #HDxxxxxxxx:" instead of "PokerStars Hand #"
      - Hand ID uses an "HD" prefix
      - No currency suffix in the stakes header (no "USD"/"EUR")
      - Timestamps have no timezone
      - Hero is already named "Hero" — no detection/replacement needed
      - Showdown marker: "*** SHOWDOWN ***" (no space) vs "*** SHOW DOWN ***"
      - Summary has extra fields after Rake: Jackpot, Bingo, Fortune, Tax
      - "Dealt to <player>" lines appear for all players (no cards for opponents)

    Inherits the full analytics engine from PokerStars → Ladbrooks chain.
    """

    def __init__(self, data, hero_name=None):
        super().__init__(data, hero_name=hero_name or 'Hero')

    # ------------------------------------------------------------------ #
    #  Splitting                                                           #
    # ------------------------------------------------------------------ #

    def split_hands(self):
        text = self.data.lstrip('\ufeff')
        parts = re.split(r'(?=Poker Hand #HD)', text)
        return [p for p in parts if p.strip()]

    # ------------------------------------------------------------------ #
    #  Validation                                                          #
    # ------------------------------------------------------------------ #

    def validate_hand(self, hand):
        first_line = hand.split('\n')[0]
        if 'Tournament' in first_line or 'Tourney' in first_line:
            return False
        if '6-max' not in hand and '6 max' not in hand.lower():
            return False
        if '*** HOLE CARDS ***' not in hand:
            return False
        if '*** SUMMARY ***' not in hand:
            return False
        if not re.search(r'Dealt to Hero \[', hand):
            return False
        seat_count = len(re.findall(r'^Seat \d+:', hand, re.MULTILINE))
        if seat_count < 2:
            return False
        return True

    def is_ggpoker_hands(self):
        try:
            raw_hands = self.split_hands()
            if not raw_hands:
                return False, "No GGPoker hand histories found.", []

            valid_hands = []
            for h in raw_hands:
                if not self.validate_hand(h):
                    continue
                if 'Hero' not in h:
                    continue
                valid_hands.append(h)

            if not valid_hands:
                return False, "No valid 6-max cash game hands found.", []

            return True, f"Found {len(valid_hands)} valid hands", valid_hands
        except Exception as e:
            return False, f"Validation Error: {e}", []

    # ------------------------------------------------------------------ #
    #  Header                                                              #
    # ------------------------------------------------------------------ #

    def parse_hand_header(self, hand):
        header = {}

        m = re.search(r'Poker Hand #(HD\d+)', hand)
        header['hand_id'] = m.group(1) if m else 'unknown'
        header['site'] = 'GGPoker'

        stakes = self._extract_stakes_from_hand(hand)
        header['stakes_sb'] = stakes[0] if stakes else 0.0
        header['stakes_bb'] = stakes[1] if stakes else 0.0

        ts_match = re.search(
            r'(\d{4}/\d{2}/\d{2})\s+(\d{1,2}:\d{2}:\d{2})', hand
        )
        if ts_match:
            try:
                from datetime import datetime
                header['timestamp'] = datetime.strptime(
                    f"{ts_match.group(1)} {ts_match.group(2)}", '%Y/%m/%d %H:%M:%S'
                )
            except ValueError:
                header['timestamp'] = None
        else:
            header['timestamp'] = None

        m = re.search(r"Table '([^']+)'\s+(\d+)-max", hand)
        if m:
            header['table_name'] = m.group(1)
            header['max_players'] = int(m.group(2))
        else:
            header['table_name'] = ''
            header['max_players'] = 6

        m = re.search(r'Seat #(\d+) is the button', hand)
        header['button_seat'] = int(m.group(1)) if m else None

        active_seats = self._count_active_seats(hand)
        header['players_dealt_in'] = active_seats

        header['game_type'] = "Texas Hold'em"
        header['limit_type'] = 'NL' if 'No Limit' in hand else ('PL' if 'Pot Limit' in hand else 'FL')
        header['currency'] = 'USD'

        lines = hand.split('\n')
        header['raw_header_line'] = lines[0].strip() if lines else ''
        return header

    # ------------------------------------------------------------------ #
    #  Raw Hand normalization                                              #
    # ------------------------------------------------------------------ #

    def _normalize_raw_hand(self, raw_hand):
        """Extends PokerStars normalization to also handle GG-specific
        markers like *** SHOWDOWN *** (no space between words)."""
        if not raw_hand:
            return raw_hand

        text = raw_hand.replace('*** SHOWDOWN ***', '')
        text = super()._normalize_raw_hand(text)
        return text

    # ------------------------------------------------------------------ #
    #  Actions — handle *** SHOWDOWN *** as a break point                  #
    # ------------------------------------------------------------------ #

    def parse_actions(self, hand, stakes_sb, stakes_bb):
        """GG uses *** SHOWDOWN *** (no space). Normalise it before
        delegating to the parent PokerStars parser."""
        normalised = hand.replace('*** SHOWDOWN ***', '*** SHOW DOWN ***')
        return super().parse_actions(normalised, stakes_sb, stakes_bb)

    # ------------------------------------------------------------------ #
    #  Summary — handle extra rake fields                                  #
    # ------------------------------------------------------------------ #

    def parse_summary(self, hand):
        """GG summary line includes Jackpot/Bingo/Fortune/Tax fields after
        Rake. The parent regex already handles this because it uses a
        non-greedy match up to the Rake portion. We also need to handle:
          - *** SHOWDOWN *** marker (no space between words)
          - "won ($X)" in seat summary lines (PS/Ladbrokes use "collected")
        """
        normalised = hand.replace('*** SHOWDOWN ***', '*** SHOW DOWN ***')
        normalised = re.sub(r'\bwon \(', 'collected (', normalised)
        return super().parse_summary(normalised)

    # ------------------------------------------------------------------ #
    #  Hero summary helper                                                 #
    # ------------------------------------------------------------------ #

    def get_hero_summary(self, hand):
        normalised = hand.replace('*** SHOWDOWN ***', '*** SHOW DOWN ***')
        return super().get_hero_summary(normalised)

    # ------------------------------------------------------------------ #
    #  Main entry point                                                    #
    # ------------------------------------------------------------------ #

    def process_ggpoker(self):
        try:
            is_valid, reason, valid_hands = self.is_ggpoker_hands()
            if not is_valid:
                return False, reason, pd.DataFrame(), {}
            dataframe = self.process_hands(valid_hands)
            if dataframe is None or dataframe.empty:
                return False, "No valid hands could be processed", pd.DataFrame(), pd.DataFrame()
            results_df = self.advanced_processing(dataframe)
            if results_df is None or results_df.empty:
                return False, "Failed to generate results", dataframe, pd.DataFrame()
            return is_valid, reason, dataframe, results_df
        except Exception as e:
            import traceback
            print(f"Error in process_ggpoker: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return False, f"Processing error: {str(e)}", pd.DataFrame(), pd.DataFrame()
