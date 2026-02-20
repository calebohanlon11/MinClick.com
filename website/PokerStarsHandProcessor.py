import re
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
from .LadbrooksPokerHandProcessor import (
    LadbrooksPokerHandProcessor, HandHistory, SeatInfo, Action, PlayerResult
)


class PokerStarsHandProcessor(LadbrooksPokerHandProcessor):
    """Processor for PokerStars cash-game hand histories (6-max).

    Inherits all calculation / analytics methods from LadbrooksPokerHandProcessor
    and overrides only the text-parsing layer to handle the PokerStars format.
    Tournament hands and non-6-max tables are automatically filtered out.
    """

    def __init__(self, data, hero_name=None):
        super().__init__(data)
        self.hero_name = hero_name

    # ------------------------------------------------------------------ #
    #  Hero-name helpers                                                   #
    # ------------------------------------------------------------------ #

    def _detect_hero_name(self, hand_text):
        m = re.search(r'Dealt to (.+?) \[', hand_text)
        return m.group(1).strip() if m else None

    def _replace_hero_name(self, hand_text, hero_name):
        return hand_text.replace(hero_name, 'Hero')

    # ------------------------------------------------------------------ #
    #  Splitting & Validation                                              #
    # ------------------------------------------------------------------ #

    def split_hands(self):
        parts = re.split(r'(?=PokerStars Hand #)', self.data)
        return [p for p in parts if p.strip()]

    def _extract_stakes_from_hand(self, hand):
        m = re.search(r'\(\$?([\d.]+)/\$?([\d.]+)\s*(?:USD|EUR|GBP)?\)', hand)
        if m:
            return float(m.group(1)), float(m.group(2))
        return None

    def validate_hand(self, hand):
        first_line = hand.split('\n')[0]
        if 'Tournament' in first_line:
            return False
        if '6-max' not in hand:
            return False
        if '*** HOLE CARDS ***' not in hand:
            return False
        if '*** SUMMARY ***' not in hand:
            return False
        if not re.search(r'Dealt to .+ \[', hand):
            return False
        return True

    def is_pokerstars_hands(self):
        try:
            raw_hands = self.split_hands()
            if not raw_hands:
                return False, "No PokerStars hand histories found.", []

            if not self.hero_name:
                for h in raw_hands:
                    detected = self._detect_hero_name(h)
                    if detected:
                        self.hero_name = detected
                        break

            if not self.hero_name:
                return False, "Could not detect hero name from hand histories.", []

            valid_hands = []
            for h in raw_hands:
                if not self.validate_hand(h):
                    continue
                if self.hero_name not in h:
                    continue
                h = self._replace_hero_name(h, self.hero_name)
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

        m = re.search(r'PokerStars Hand #(\d+)', hand)
        header['hand_id'] = m.group(1) if m else 'unknown'
        header['site'] = 'PokerStars'

        stakes = self._extract_stakes_from_hand(hand)
        header['stakes_sb'] = stakes[0] if stakes else 0.0
        header['stakes_bb'] = stakes[1] if stakes else 0.0

        m = re.search(r'(\d{4}/\d{2}/\d{2})\s+(\d{1,2}:\d{2}:\d{2})\s+\w+', hand)
        if m:
            try:
                header['timestamp'] = datetime.strptime(
                    f"{m.group(1)} {m.group(2)}", '%Y/%m/%d %H:%M:%S'
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
        header['limit_type'] = 'NL' if 'No Limit' in hand else 'FL'

        if 'USD' in hand:
            header['currency'] = 'USD'
        elif 'EUR' in hand:
            header['currency'] = 'EUR'
        elif 'GBP' in hand:
            header['currency'] = 'GBP'
        else:
            header['currency'] = 'USD'

        lines = hand.split('\n')
        header['raw_header_line'] = lines[0].strip() if lines else ''
        return header

    def _count_active_seats(self, hand):
        count = 0
        for line in hand.split('\n'):
            line = line.strip()
            if re.match(r'Seat \d+:', line) and '(in chips)' in line.lower() or 'in chips' in line:
                if 'is sitting out' not in line:
                    count += 1
        return count if count > 0 else 6

    # ------------------------------------------------------------------ #
    #  Seats                                                               #
    # ------------------------------------------------------------------ #

    def parse_seat_information(self, hand):
        seats = []
        for line in hand.split('\n'):
            line = line.strip()
            if 'is sitting out' in line:
                continue
            m = re.match(r'Seat (\d+): (.+?) \(\$?([\d.]+) in chips\)', line)
            if m:
                seats.append(SeatInfo(
                    seat_number=int(m.group(1)),
                    player_name=m.group(2).strip(),
                    starting_stack=float(m.group(3)),
                    is_hero=(m.group(2).strip() == 'Hero')
                ))
        return seats

    # ------------------------------------------------------------------ #
    #  Hole Cards                                                          #
    # ------------------------------------------------------------------ #

    def parse_hero_hole_cards(self, hand):
        m = re.search(r'Dealt to Hero \[(\S+)\s+(\S+)\]', hand)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None, None

    # ------------------------------------------------------------------ #
    #  Board Cards                                                         #
    # ------------------------------------------------------------------ #

    def parse_board_cards(self, hand):
        board = {
            'flop_card_1': None, 'flop_card_2': None, 'flop_card_3': None,
            'turn_card': None, 'river_card': None,
            'board_flop': [], 'board_turn': [], 'board_river': [], 'board_all': []
        }

        m = re.search(r'\*\*\* FLOP \*\*\* \[(\S+)\s+(\S+)\s+(\S+)\]', hand)
        if m:
            board['flop_card_1'] = m.group(1)
            board['flop_card_2'] = m.group(2)
            board['flop_card_3'] = m.group(3)
            board['board_flop'] = [m.group(1), m.group(2), m.group(3)]
            board['board_all'] = list(board['board_flop'])

        m = re.search(r'\*\*\* TURN \*\*\* \[.+?\] \[(\S+)\]', hand)
        if m:
            board['turn_card'] = m.group(1)
            board['board_turn'] = board['board_flop'] + [m.group(1)]
            board['board_all'] = list(board['board_turn'])

        m = re.search(r'\*\*\* RIVER \*\*\* \[.+?\] \[(\S+)\]', hand)
        if m:
            board['river_card'] = m.group(1)
            prev = board['board_turn'] or board['board_flop']
            board['board_river'] = prev + [m.group(1)]
            board['board_all'] = list(board['board_river'])

        return board

    # ------------------------------------------------------------------ #
    #  Actions                                                             #
    # ------------------------------------------------------------------ #

    def parse_actions(self, hand, stakes_sb, stakes_bb):
        actions = []
        action_index = 0
        pot = 0.0

        seats = self.parse_seat_information(hand)
        stacks = {s.player_name: s.starting_stack for s in seats}

        current_street = None
        current_bet = 0.0
        player_round_inv = {}

        for line in hand.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Street transitions
            if line.startswith('*** HOLE CARDS ***'):
                current_street = 'preflop'
                continue
            if line.startswith('*** FLOP ***'):
                current_street = 'flop'
                current_bet = 0.0
                player_round_inv = {}
                continue
            if line.startswith('*** TURN ***'):
                current_street = 'turn'
                current_bet = 0.0
                player_round_inv = {}
                continue
            if line.startswith('*** RIVER ***'):
                current_street = 'river'
                current_bet = 0.0
                player_round_inv = {}
                continue
            if line.startswith('*** SHOW DOWN ***') or line.startswith('*** SUMMARY ***'):
                break

            # --- Blind posts (before HOLE CARDS) ---
            if current_street is None:
                m = re.match(r'(.+?): posts small blind \$?([\d.]+)', line)
                if m:
                    player, amount = m.group(1), float(m.group(2))
                    pot_before = pot
                    pot += amount
                    stacks[player] = stacks.get(player, 0) - amount
                    player_round_inv[player] = amount
                    current_bet = max(current_bet, amount)
                    actions.append(Action(
                        street='preflop', action_index=action_index,
                        actor=player, action_type='post_sb',
                        amount=amount, to_call_before=0.0,
                        stack_before=stacks[player] + amount,
                        stack_after=stacks[player],
                        pot_before=pot_before, pot_after=pot,
                        is_all_in=False
                    ))
                    action_index += 1
                    continue

                m = re.match(r'(.+?): posts big blind \$?([\d.]+)', line)
                if m:
                    player, amount = m.group(1), float(m.group(2))
                    pot_before = pot
                    pot += amount
                    stacks[player] = stacks.get(player, 0) - amount
                    player_round_inv[player] = amount
                    current_bet = max(current_bet, amount)
                    actions.append(Action(
                        street='preflop', action_index=action_index,
                        actor=player, action_type='post_bb',
                        amount=amount, to_call_before=0.0,
                        stack_before=stacks[player] + amount,
                        stack_after=stacks[player],
                        pot_before=pot_before, pot_after=pot,
                        is_all_in=False
                    ))
                    action_index += 1
                    continue
                continue

            # --- Uncalled bet return (not a real action, but adjusts pot/stacks) ---
            m_unc = re.match(r'Uncalled bet \(\$?([\d.]+)\) returned to (.+)', line)
            if m_unc:
                amount = float(m_unc.group(1))
                player = m_unc.group(2).strip()
                pot -= amount
                stacks[player] = stacks.get(player, 0) + amount
                if player in player_round_inv:
                    player_round_inv[player] -= amount
                continue

            # Skip non-action lines
            if ': ' not in line:
                continue
            if line.startswith('Dealt to'):
                continue
            skip_keywords = [
                'collected', "doesn't show", 'shows [', 'mucks hand',
                'joins the table', 'leaves the table', 'has timed out',
                'is disconnected', 'is sitting out', 'said,', 'was removed',
                'finished the tournament'
            ]
            if any(kw in line for kw in skip_keywords):
                continue

            colon_idx = line.find(': ')
            if colon_idx == -1:
                continue
            player = line[:colon_idx]
            action_text = line[colon_idx + 2:]

            if player not in stacks:
                continue

            is_all_in = 'and is all-in' in action_text
            clean = action_text.replace(' and is all-in', '').strip()

            action_obj = None
            pot_before = pot
            to_call = current_bet

            if clean == 'folds':
                action_obj = Action(
                    street=current_street, action_index=action_index,
                    actor=player, action_type='fold',
                    amount=0.0, to_call_before=to_call,
                    stack_before=stacks[player], stack_after=stacks[player],
                    pot_before=pot_before, pot_after=pot,
                    is_all_in=False
                )

            elif clean == 'checks':
                action_obj = Action(
                    street=current_street, action_index=action_index,
                    actor=player, action_type='check',
                    amount=0.0, to_call_before=0.0,
                    stack_before=stacks[player], stack_after=stacks[player],
                    pot_before=pot_before, pot_after=pot,
                    is_all_in=False
                )

            elif clean.startswith('calls'):
                m = re.match(r'calls \$?([\d.]+)', clean)
                if m:
                    amt = float(m.group(1))
                    pot += amt
                    stacks[player] -= amt
                    player_round_inv[player] = player_round_inv.get(player, 0) + amt
                    action_obj = Action(
                        street=current_street, action_index=action_index,
                        actor=player, action_type='call',
                        amount=amt, to_call_before=to_call,
                        stack_before=stacks[player] + amt,
                        stack_after=stacks[player],
                        pot_before=pot_before, pot_after=pot,
                        is_all_in=is_all_in or stacks[player] == 0
                    )

            elif clean.startswith('bets'):
                m = re.match(r'bets \$?([\d.]+)', clean)
                if m:
                    amt = float(m.group(1))
                    pot += amt
                    stacks[player] -= amt
                    player_round_inv[player] = amt
                    current_bet = amt
                    pct = (amt / pot_before * 100) if pot_before > 0 else 0
                    action_obj = Action(
                        street=current_street, action_index=action_index,
                        actor=player, action_type='bet',
                        amount=amt, to_call_before=to_call,
                        bet_size_total=amt, bet_size_pct_pot=pct,
                        stack_before=stacks[player] + amt,
                        stack_after=stacks[player],
                        pot_before=pot_before, pot_after=pot,
                        is_all_in=is_all_in or stacks[player] == 0
                    )

            elif clean.startswith('raises'):
                m = re.match(r'raises \$?([\d.]+) to \$?([\d.]+)', clean)
                if m:
                    raise_to = float(m.group(2))
                    prev_inv = player_round_inv.get(player, 0)
                    new_money = raise_to - prev_inv
                    pot += new_money
                    stacks[player] -= new_money
                    player_round_inv[player] = raise_to
                    current_bet = raise_to
                    pct = (new_money / pot_before * 100) if pot_before > 0 else 0
                    action_obj = Action(
                        street=current_street, action_index=action_index,
                        actor=player,
                        action_type='all_in' if is_all_in else 'raise',
                        amount=new_money, to_call_before=to_call,
                        bet_size_total=raise_to, bet_size_pct_pot=pct,
                        stack_before=stacks[player] + new_money,
                        stack_after=stacks[player],
                        pot_before=pot_before, pot_after=pot,
                        is_all_in=is_all_in or stacks[player] == 0
                    )

            if action_obj:
                actions.append(action_obj)
                action_index += 1

        return actions

    # ------------------------------------------------------------------ #
    #  Summary                                                             #
    # ------------------------------------------------------------------ #

    def parse_summary(self, hand):
        summary = {
            'final_pot': 0.0, 'rake': 0.0,
            'board_final': [], 'side_pots': [],
            'player_results': []
        }

        if '*** SUMMARY ***' not in hand:
            return summary

        summary_section = hand.split('*** SUMMARY ***')[1]

        # Total pot & rake
        m = re.search(r'Total pot \$?([\d.]+).*?\|\s*Rake \$?([\d.]+)', summary_section)
        if m:
            summary['final_pot'] = float(m.group(1))
            summary['rake'] = float(m.group(2))

        # Side pots
        for sp in re.finditer(r'Side pot(?:-\d+)? \$?([\d.]+)', summary_section):
            summary['side_pots'].append(float(sp.group(1)))

        # Board
        m = re.search(r'Board \[(.+?)\]', summary_section)
        if m:
            summary['board_final'] = m.group(1).strip().split()

        # ---- Per-player contributions & collections ---- #
        seats = self.parse_seat_information(hand)
        starting_stacks = {s.player_name: s.starting_stack for s in seats}
        contributions = {s.player_name: 0.0 for s in seats}
        player_round_inv = {}

        pre_summary = hand.split('*** SUMMARY ***')[0]
        for line in pre_summary.split('\n'):
            line = line.strip()

            if line.startswith('*** FLOP ***') or line.startswith('*** TURN ***') or line.startswith('*** RIVER ***'):
                player_round_inv = {}
                continue

            # Blind posts
            m_sb = re.match(r'(.+?): posts small blind \$?([\d.]+)', line)
            if m_sb:
                p, amt = m_sb.group(1), float(m_sb.group(2))
                contributions[p] = contributions.get(p, 0) + amt
                player_round_inv[p] = amt
                continue
            m_bb = re.match(r'(.+?): posts big blind \$?([\d.]+)', line)
            if m_bb:
                p, amt = m_bb.group(1), float(m_bb.group(2))
                contributions[p] = contributions.get(p, 0) + amt
                player_round_inv[p] = amt
                continue

            # Uncalled bet return
            m_unc = re.match(r'Uncalled bet \(\$?([\d.]+)\) returned to (.+)', line)
            if m_unc:
                amt = float(m_unc.group(1))
                p = m_unc.group(2).strip()
                contributions[p] = contributions.get(p, 0) - amt
                continue

            if ': ' not in line:
                continue
            ci = line.find(': ')
            p = line[:ci]
            act = line[ci + 2:].replace(' and is all-in', '').strip()

            if p not in contributions:
                continue

            if act.startswith('calls'):
                m = re.match(r'calls \$?([\d.]+)', act)
                if m:
                    amt = float(m.group(1))
                    contributions[p] += amt
                    player_round_inv[p] = player_round_inv.get(p, 0) + amt
            elif act.startswith('bets'):
                m = re.match(r'bets \$?([\d.]+)', act)
                if m:
                    amt = float(m.group(1))
                    contributions[p] += amt
                    player_round_inv[p] = amt
            elif act.startswith('raises'):
                m = re.match(r'raises \$?([\d.]+) to \$?([\d.]+)', act)
                if m:
                    raise_to = float(m.group(2))
                    prev = player_round_inv.get(p, 0)
                    new_money = raise_to - prev
                    contributions[p] += new_money
                    player_round_inv[p] = raise_to

        # Collections
        collections = {s.player_name: 0.0 for s in seats}
        all_text = pre_summary + '\n' + summary_section
        for m in re.finditer(r'(\S+) collected \$?([\d.]+) from', all_text):
            p, amt = m.group(1).strip(), float(m.group(2))
            if p in collections:
                collections[p] += amt

        # ---- Build PlayerResult for each seat from summary lines ---- #
        for line in summary_section.split('\n'):
            line = line.strip()
            m = re.match(r'Seat \d+: (\S+)', line)
            if not m:
                continue
            player = m.group(1)
            if player not in starting_stacks:
                continue

            contrib = contributions.get(player, 0)
            collected = collections.get(player, 0)
            net = round(collected - contrib, 2)
            ending = round(starting_stacks[player] + net, 2)

            showed_down = False
            won_pot = collected > 0
            final_cards = None
            final_desc = None

            cards_m = re.search(r'showed \[(.+?)\]', line)
            if cards_m:
                showed_down = True
                final_cards = cards_m.group(1).strip().split()
            mucked_m = re.search(r'mucked \[(.+?)\]', line)
            if mucked_m:
                showed_down = True
                final_cards = mucked_m.group(1).strip().split()

            desc_m = re.search(r'with (.+)$', line)
            if desc_m:
                final_desc = desc_m.group(1).strip()

            summary['player_results'].append(PlayerResult(
                player_name=player,
                ending_stack=ending,
                net_result=net,
                amount_contributed=round(contrib, 2),
                won_pot=won_pot,
                showed_down=showed_down,
                final_hand_cards=final_cards,
                final_hand_description=final_desc
            ))

        return summary

    # ------------------------------------------------------------------ #
    #  Raw Hand normalization (Ladbrokes compat for downstream analytics)  #
    # ------------------------------------------------------------------ #

    def _normalize_raw_hand(self, raw_hand):
        """Convert PokerStars section markers and action lines to Ladbrokes
        format so that downstream analytics (flop action freq, biggest hands,
        VPIP fallback, etc.) work without modification."""
        if not raw_hand:
            return raw_hand

        text = raw_hand

        # Inject "Total number of players :" before seat lines (needed by
        # get_seat_info, _get_villain_position_from_raw_hand, etc.)
        active_count = 0
        for line in text.split('\n'):
            line = line.strip()
            if re.match(r'Seat \d+:', line) and 'in chips' in line and 'is sitting out' not in line:
                active_count += 1
        if active_count and 'Total number of players :' not in text:
            text = re.sub(
                r'(Seat \d+:)',
                f'Total number of players : {active_count}/{active_count}\n\\1',
                text,
                count=1
            )

        # Section markers
        text = text.replace('*** HOLE CARDS ***', '** Dealing down cards **')
        text = re.sub(
            r'\*\*\* FLOP \*\*\* \[(\S+)\s+(\S+)\s+(\S+)\]',
            r'** Dealing Flop ** [ \1, \2, \3 ]',
            text
        )
        text = re.sub(
            r'\*\*\* TURN \*\*\* \[.+?\] \[(\S+)\]',
            r'** Dealing Turn ** [ \1 ]',
            text
        )
        text = re.sub(
            r'\*\*\* RIVER \*\*\* \[.+?\] \[(\S+)\]',
            r'** Dealing River ** [ \1 ]',
            text
        )
        text = text.replace('*** SHOW DOWN ***', '')
        text = text.replace('*** SUMMARY ***', '** Summary **')

        # Button seat: "Seat #5 is the button" → "Seat 5 is the button"
        text = re.sub(r'Seat #(\d+) is the button', r'Seat \1 is the button', text)

        # Action lines: remove colon separator and normalise amounts
        # "Player: calls $0.12" → "Player calls (0.12)"
        normalised_lines = []
        action_kw = re.compile(
            r'^(.+?):\s+(calls|bets|raises|folds|checks|posts small blind|posts big blind)\s*(.*)',
            re.IGNORECASE
        )
        for line in text.split('\n'):
            m = action_kw.match(line.strip())
            if m:
                player = m.group(1)
                verb = m.group(2)
                rest = m.group(3)
                rest = re.sub(r'\$?([\d.]+)', r'(\1)', rest)
                rest = rest.replace(' and is all-in', ' [all-In]')
                if verb == 'raises':
                    to_m = re.search(r'to \(([\d.]+)\)', rest)
                    if to_m:
                        rest = f'({to_m.group(1)})'
                normalised_lines.append(f'{player} {verb} {rest}'.rstrip())
            else:
                normalised_lines.append(line)
        text = '\n'.join(normalised_lines)
        return text

    def parse_hand_to_history(self, hand):
        hh = super().parse_hand_to_history(hand)
        if hh and hh.raw_hand:
            hh.raw_hand = self._normalize_raw_hand(hh.raw_hand)
        return hh

    def get_button_seat(self, hand):
        m = re.search(r'Seat #?(\d+) is the button', hand)
        return int(m.group(1)) if m else None

    def get_seat_info(self, hand):
        """Extract (seat_number, player_name) tuples from PokerStars hand."""
        seat_info = []
        for line in hand.split('\n'):
            line = line.strip()
            if 'is sitting out' in line:
                continue
            m = re.match(r'Seat (\d+): (.+?) \(\$?([\d.]+)', line)
            if m:
                seat_info.append((int(m.group(1)), m.group(2).strip()))
        return seat_info

    # ------------------------------------------------------------------ #
    #  Main entry point                                                    #
    # ------------------------------------------------------------------ #

    def process_pokerstars(self):
        try:
            is_valid, reason, valid_hands = self.is_pokerstars_hands()
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
            print(f"Error in process_pokerstars: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return False, f"Processing error: {str(e)}", pd.DataFrame(), pd.DataFrame()
