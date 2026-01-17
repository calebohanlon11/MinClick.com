import pandas as pd
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class SeatInfo:
    """Information about a seat at the table"""
    seat_number: int
    player_name: str
    starting_stack: float
    is_hero: bool

@dataclass
class Action:
    """A single action in the hand"""
    street: str  # "preflop", "flop", "turn", "river"
    action_index: int  # Global index across all streets
    actor: str  # Player name
    action_type: str  # "fold", "check", "call", "bet", "raise", "all_in", "post_sb", "post_bb", etc.
    amount: float  # Amount newly put into pot by this action
    to_call_before: float  # Amount needed to call before this action
    bet_size_total: Optional[float] = None  # Final total bet/raise size after action
    stack_before: Optional[float] = None
    stack_after: Optional[float] = None
    pot_before: Optional[float] = None
    pot_after: Optional[float] = None
    is_all_in: bool = False
    bet_size_pct_pot: Optional[float] = None  # Bet size as % of pot before bet

@dataclass
class PlayerResult:
    """Results for a single player"""
    player_name: str
    ending_stack: float
    net_result: float  # ending_stack - starting_stack
    amount_contributed: float
    won_pot: bool
    showed_down: bool
    final_hand_cards: Optional[List[str]] = None
    final_hand_description: Optional[str] = None

@dataclass
class HandHistory:
    """Complete parsed hand history with raw and derived fields"""
    # Hand-level metadata (raw)
    hand_id: str
    site: str = "LabWorks"
    table_name: str = ""
    stakes_sb: float = 0.0
    stakes_bb: float = 0.0
    currency: str = "USD"
    game_type: str = "Texas Hold'em"
    limit_type: str = "NL"
    max_players: int = 6
    players_dealt_in: int = 0
    button_seat: Optional[int] = None
    timestamp: Optional[datetime] = None
    raw_header_line: str = ""
    
    # Seat information (raw)
    seats: List[SeatInfo] = field(default_factory=list)
    
    # Hole cards (raw)
    hero_hole_card_1: Optional[str] = None
    hero_hole_card_2: Optional[str] = None
    
    # Board cards (raw)
    flop_card_1: Optional[str] = None
    flop_card_2: Optional[str] = None
    flop_card_3: Optional[str] = None
    turn_card: Optional[str] = None
    river_card: Optional[str] = None
    board_flop: List[str] = field(default_factory=list)
    board_turn: List[str] = field(default_factory=list)
    board_river: List[str] = field(default_factory=list)
    board_all: List[str] = field(default_factory=list)
    
    # Unified action list (raw + derived)
    actions: List[Action] = field(default_factory=list)
    
    # Summary data (raw)
    final_pot: float = 0.0
    rake: float = 0.0
    board_final: List[str] = field(default_factory=list)
    side_pots: List[Dict] = field(default_factory=list)
    player_results: List[PlayerResult] = field(default_factory=list)
    
    # Hero-specific results (derived)
    hero_net_result_chips: float = 0.0
    hero_net_result_bb: float = 0.0
    hero_went_to_showdown: bool = False
    hero_won_at_showdown: bool = False
    hero_won_without_showdown: bool = False
    
    # Derived preflop analytics
    hero_preflop_absolute_position: Optional[str] = None  # "UTG", "HJ", "CO", "BTN", "SB", "BB"
    opened_pot: bool = False  # Hero was first raiser (RFI)
    limped: bool = False
    had_3bet_opportunity: bool = False
    did_3bet: bool = False
    had_4bet_opportunity: bool = False
    did_4bet: bool = False
    faced_open_raise: bool = False
    faced_3bet: bool = False
    faced_4bet: bool = False
    preflop_role: Optional[str] = None  # "open_raiser", "cold_caller", "3_bettor", "4_bettor", "caller_vs_3bet", "squeezer", "iso_raiser"
    preflop_aggressor: Optional[str] = None  # Player name of last person to make biggest raise
    
    # Postflop metrics
    table_size_at_start: int = 6
    players_see_flop: int = 0
    players_see_turn: int = 0
    players_see_river: int = 0
    hero_saw_flop: bool = False
    hero_saw_turn: bool = False
    hero_saw_river: bool = False
    players_active_on_flop: List[str] = field(default_factory=list)
    players_active_on_turn: List[str] = field(default_factory=list)
    players_active_on_river: List[str] = field(default_factory=list)
    hero_is_active_on_flop: bool = False
    hero_is_active_on_turn: bool = False
    hero_is_active_on_river: bool = False
    
    # Action order (Hero)
    hero_action_order_index_flop: Optional[int] = None
    hero_action_order_count_flop: Optional[int] = None
    hero_relative_position_category_flop: Optional[str] = None  # "first_to_act", "MP", "last_to_act"
    hero_position_vs_preflop_raiser_flop: Optional[str] = None  # "OOP", "MP", "IP" (based on postflop action order)
    
    hero_action_order_index_turn: Optional[int] = None
    hero_action_order_count_turn: Optional[int] = None
    hero_relative_position_category_turn: Optional[str] = None
    hero_position_vs_preflop_raiser_turn: Optional[str] = None
    
    hero_action_order_index_river: Optional[int] = None
    hero_action_order_count_river: Optional[int] = None
    hero_relative_position_category_river: Optional[str] = None
    hero_position_vs_preflop_raiser_river: Optional[str] = None
    
    # Store raw hand for reference
    raw_hand: str = ""

class LadbrooksPokerHandProcessor:
    def __init__(self, data):
        self.data = data

    def split_hands(self):
        hands = self.data.split('***** Hand History For Game')
        hands = [f'***** Hand History For Game{hand}' for hand in hands if hand.strip() != '']
        return hands

    def get_button_seat(self, hand):
        for line in hand.split('\n'):
            if "is the button" in line:
                return int(line.split('Seat ')[1].split(' is the button')[0])
        return None

    def get_big_blind(self, hand):
        big_blind = small_blind = 0
        for line in hand.split('\n'):
            if "posts big blind" in line:
                big_blind = float(line.split('(')[1].split(')')[0])
            if "posts small blind" in line:
                small_blind = float(line.split('(')[1].split(')')[0])
        return big_blind, small_blind

    def get_seat_info(self, hand):
        seat_info_lines = hand.split('Total number of players :')[1].split('** Dealing down cards **')[0].strip().split('\n')
        seat_info = []
        for line in seat_info_lines:
            if 'Seat' in line:
                seat_num = int(line.split('Seat ')[1].split(':')[0].strip())
                player_name = line.split(': ')[1].split(' ($')[0].strip()
                seat_info.append((seat_num, player_name))
        return seat_info

    def calculate_positions(self, seat_info, button_seat, total_players):
        """Map players to positions using the same logic as calculate_hero_position for consistency."""
        if button_seat is None or not seat_info:
            return {}

        # Use the same position calculation logic as calculate_hero_position
        # Sort seats by seat number
        sorted_seats = sorted(seat_info, key=lambda x: x[0])
        
        # Find button index
        button_index = None
        for i, (seat_num, _) in enumerate(sorted_seats):
            if seat_num == button_seat:
                button_index = i
                break
        
        if button_index is None:
            return {}
        
        # Position names based on table size (same as calculate_hero_position)
        if total_players == 2:
            positions = ['SB', 'BB']
        elif total_players == 3:
            positions = ['BTN', 'SB', 'BB']
        elif total_players == 4:
            positions = ['CO', 'BTN', 'SB', 'BB']
        elif total_players == 5:
            positions = ['MP', 'CO', 'BTN', 'SB', 'BB']
        else:  # 6 handed
            positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        
        # Calculate BTN index in positions array (same logic as calculate_hero_position)
        #   2-handed: button is at SB (index 0)
        #   3-handed: button is at BTN (index 0)
        #   4+ handed: button is at BTN at index (total_players - 3)
        if total_players == 2:
            btn_index_in_positions = 0  # Button is at SB
        elif total_players == 3:
            btn_index_in_positions = 0  # Button is at BTN
        else:
            btn_index_in_positions = total_players - 3  # BTN position index
        
        # Map each player to their position
        position_map = {}
        for i, (seat_num, player_name) in enumerate(sorted_seats):
            # Calculate offset from button
            offset_from_button = (i - button_index) % total_players
            # Map offset to position index
            position_index = (btn_index_in_positions + offset_from_button) % len(positions)
            position_map[player_name] = positions[position_index]
        
        return position_map

    def get_pre_flop_data(self, hand):
        if "** Dealing Flop **" in hand:
            pre_flop_data = hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0].strip()
            return pre_flop_data, True
        else:
            pre_flop_data = hand.split('** Dealing down cards **')[1].split('** Summary **')[0].strip()
            return pre_flop_data, False

    def get_hero_summary(self, summary):
        for line in summary.split('\n'):
            if 'Hero balance' in line:
                return line.strip()
        return "Hero balance info not found"

    def process_summary(self, hand_summary):
        def extract_numeric_value(string):
            # Extract first numeric value (handles formats like "14.67[ 6s, 8s ]" or "1.72")
            match = re.search(r"[-+]?\d+\.?\d*", string)
            if match:
                return float(match.group())
            return 0.0

        if not hand_summary or not isinstance(hand_summary, str):
            return 0.0, False

        hand_result = 0.0
        summary_lower = hand_summary.lower()
        summary_original = hand_summary  # Keep original for exact matching

        # VPIP = Voluntarily Put In Pot
        # Default to False; only True if Hero voluntarily put money in (not just blinds)
        vpip = False
        
        # Check for reconstructed format: "Hero balance $X.XX, net +Y.YY" or "net -Y.YY"
        if "net " in summary_original and ("balance" in summary_original or "Hero" in summary_original):
            net_match = re.search(r"net\s+([+-]?\d+\.?\d*)", summary_original)
            if net_match:
                hand_result = float(net_match.group(1))
                vpip = hand_result != 0.0  # If net is non-zero, likely VPIP (will be refined by action check)
        # Check for "net +$" format (Hero won money)
        elif "net +$" in summary_original:
            net_result_part = summary_original.split('net +$')[1]
            hand_result = extract_numeric_value(net_result_part)
            vpip = True  # Won money = definitely VPIP
        # Check for "lost $" (Hero lost money)
        elif "lost $" in summary_original:
            lost_part = summary_original.split('lost $')[1]
            hand_result = -extract_numeric_value(lost_part)
            # Mark as potential VPIP (will be refined by action summary check)
            vpip = True
        # Check for "didn't bet" (Hero folded without putting money in)
        elif "didn't bet" in summary_lower:
            hand_result = 0.0
            vpip = False
        # Check for "bet $X, collected $Y" format (calculate net)
        elif "bet $" in summary_original and "collected $" in summary_original:
            try:
                bet_match = re.search(r"bet \$([\d.]+)", summary_original)
                collected_match = re.search(r"collected \$([\d.]+)", summary_original)
                if bet_match and collected_match:
                    bet_amount = float(bet_match.group(1))
                    collected_amount = float(collected_match.group(1))
                    hand_result = collected_amount - bet_amount
                    vpip = True  # Bet and collected = definitely VPIP
            except (ValueError, AttributeError):
                hand_result = 0.0
                vpip = False
        else:
            # No clear result, default to 0
            hand_result = 0.0
            vpip = False

        return hand_result, vpip

    def create_package_for_raise(self, raise_level, raise_or_call, size, size_from, players_in_pot, pot_size):
        raise_levels = ['limp', 'rfi', 'three_bet', 'four_bet', 'five_bet', 'six_bet']
        call_levels = ['limp', 'call_rfi', 'call_three_bet', 'call_four_bet', 'call_five_bet', 'call_six_bet']

        if raise_or_call == 'Fold':
            return 'fold', {"Raise_level": 'fold', "current_bet": size, 'Number_players': len(players_in_pot), 'size_pot': pot_size}

        if raise_or_call:
            return raise_levels[raise_level-1], {'Raise_from': size_from, 'Raised_to': size, 'Number_players': len(players_in_pot), 'size_pot': pot_size}

        return call_levels[raise_level-1], {'call_from': size_from, 'call_size': size, 'Number_players': len(players_in_pot), 'size_pot': pot_size}

    def action_process_summary(self, vpip, bb_stake, sb_stake, position, action_summary):
        action_data = {key: 0 for key in ['limp', 'rfi', 'call_rfi', 'three_bet', 'call_three_bet', 'four_bet', 'call_four_bet', 'five_bet', 'call_five_bet', 'six_bet', 'call_six_bet']}
        pot_size = bb_stake + sb_stake
        current_bet = bb_stake
        players_in_pot = []
        level_raised = 1

        if not vpip:
            return action_data, pot_size

        for line in action_summary.split('\n'):
            if 'Hero' in line:
                if 'Hero' not in players_in_pot and 'folds' not in line:
                    players_in_pot.append('Hero')
                if 'raises' in line:
                    level_raised += 1
                    size, size_from = self.get_action_sizes(line, current_bet, position, bb_stake, sb_stake)
                    column, data_package = self.create_package_for_raise(level_raised, raise_or_call=True, size=size, size_from=size_from, players_in_pot=players_in_pot, pot_size=pot_size)
                    action_data[column] = data_package
                    pot_size += (size-size_from)
                elif "call" in line:
                    size, size_from = self.get_action_sizes(line, current_bet, position, bb_stake, sb_stake)
                    column, data_package = self.create_package_for_raise(level_raised, raise_or_call=False, size=size, size_from=size_from, players_in_pot=players_in_pot, pot_size=pot_size)
                    action_data[column] = data_package
                    pot_size += (size-size_from)
                elif "folds" in line:
                    column, data_package = self.create_package_for_raise(level_raised, raise_or_call='Fold', size=current_bet, size_from=0, players_in_pot=players_in_pot, pot_size=pot_size)
                    action_data[column] = data_package
                    if 'Hero' in players_in_pot:
                        players_in_pot.remove('Hero')
            else:
                if 'raises' in line:
                    level_raised += 1
                    size, size_from = self.get_action_sizes(line, current_bet, position, bb_stake, sb_stake)
                    pot_size += (size-size_from)
                    current_bet = size
                    players_in_pot = self.update_players(line=line, players=players_in_pot, add=True)
                elif "call" in line:
                    size, size_from = self.get_action_sizes(line, current_bet, position, bb_stake, sb_stake)
                    pot_size += (size-size_from)
                    players_in_pot = self.update_players(line=line, players=players_in_pot, add=True)
                elif "folds" in line:
                    players_in_pot = self.update_players(line=line, players=players_in_pot, add=False)

        return action_data, pot_size

    def calculate_new_pot(self, initial_pot, ip_actions, op_actions):
        if any(action[0] == 'folds' for action in ip_actions + op_actions):
            return 0
        if any(action[0] == 'bets' for action in ip_actions + op_actions) or any('raises' in action[0] for action in ip_actions + op_actions):
            raise_amounts = [action[1] for action in ip_actions + op_actions if action[0] == 'bets' or 'raises' in action[0]]
            max_raise = max(raise_amounts)
            new_pot = initial_pot + 2 * max_raise
            return round(new_pot, 5)

        new_pot = initial_pot
        for action in ip_actions + op_actions:
            if action[0] in ['bets', 'calls']:
                new_pot += action[1]

        return round(new_pot, 5)

    def post_action_process_summary(self, HU_bool, Action_Summary, BB_Stake, pot):
        action_data = {
            key: 0 for key in [
                'flop_Position', 'flop_cards', 'flop_pot',
                'flop_OP', 'flop_IP', 'turn_cards', 'turn_pot', 'turn_OP', 'turn_IP',
                'river_cards', 'river_pot', 'river_IP', 'river_OP'
            ]
        }
        if not HU_bool:
            return action_data

        lines = Action_Summary.split('\n')
        flop_action, turn_action, river_action = [], [], []
        current_section = 'flop'

        for line in lines:
            if '** Dealing Turn **' in line:
                current_section = 'turn'
                action_data['turn_cards'] = line.split(':')[1].strip()
            elif '** Dealing River **' in line:
                current_section = 'river'
                action_data['river_cards'] = line.split(':')[1].strip()
            else:
                if current_section == 'flop':
                    if ':' in line:
                        action_data['flop_cards'] = line.split(':')[1].strip()
                    else:
                        flop_action.append(line)
                elif current_section == 'turn':
                    turn_action.append(line)
                elif current_section == 'river':
                    river_action.append(line)

        action_data['flop_pot'] = pot

        if 'Hero' in flop_action[0]:
            action_data['flop_Position'] = False
        else:
            action_data['flop_Position'] = True

        action_data['flop_OP'] = []
        action_data['flop_IP'] = []

        for i, line in enumerate(flop_action):
            player, action = line.split(' ', 1)
            action_type = action.split('(')[0].strip().lower()
            amount = float(re.findall(r'\d+\.\d+', action)[0]) if re.findall(r'\d+\.\d+', action) else 0
            action_type = re.sub(r'\(\d+\.\d+\)', '', action_type).strip()

            if i % 2 == 0:
                if action_data['flop_OP'] == 0:
                    action_data['flop_OP'] = []
                action_data['flop_OP'].append([action_type, amount])
            else:
                if action_data['flop_IP'] == 0:
                    action_data['flop_IP'] = []
                action_data['flop_IP'].append([action_type, amount])

        action_data['turn_OP'] = []
        action_data['turn_IP'] = []
        action_data['river_OP'] = []
        action_data['river_IP'] = []

        if turn_action:
            action_data['turn_pot'] = self.calculate_new_pot(pot, action_data['flop_IP'], action_data['flop_OP'])

            for i, line in enumerate(turn_action):
                player, action = line.split(' ', 1)
                action_type = action.split('(')[0].strip().lower()
                amount = float(re.findall(r'\d+\.\d+', action)[0]) if re.findall(r'\d+\.\d+', action) else 0
                action_type = re.sub(r'\(\d+\.\d+\)', '', action_type).strip()

                if i % 2 == 0:
                    if action_data['turn_OP'] == 0:
                        action_data['turn_OP'] = []
                    action_data['turn_OP'].append([action_type, amount])
                else:
                    if action_data['turn_IP'] == 0:
                        action_data['turn_IP'] = []
                    action_data['turn_IP'].append([action_type, amount])

        if river_action:
            action_data['river_pot'] = self.calculate_new_pot(action_data['turn_pot'], action_data['turn_IP'], action_data['turn_OP'])

            for i, line in enumerate(river_action):
                player, action = line.split(' ', 1)
                action_type = action.split('(')[0].strip().lower()
                amount = float(re.findall(r'\d+\.\d+', action)[0]) if re.findall(r'\d+\.\d+', action) else 0
                action_type = re.sub(r'\(\d+\.\d+\)', '', action_type).strip()

                if i % 2 == 0:
                    if action_data['river_OP'] == 0:
                        action_data['river_OP'] = []
                    action_data['river_OP'].append([action_type, amount])
                else:
                    if action_data['river_IP'] == 0:
                        action_data['river_IP'] = []
                    action_data['river_IP'].append([action_type, amount])

        return action_data

    def update_players(self, line, players, add=True):
        player = line[:7]
        if players is None:
            players = []
        if player in players:
            if not add:
                players.remove(player)
        else:
            if add:
                players.append(player)
        return players

    def get_action_sizes(self, action, current_value, position, bb_stake, sb_stake):
        if "calls" in action:
            call_amount = float(action.split('(')[1].split(')')[0])
            return round(current_value, 5), round(current_value - call_amount, 5)
        elif "raises" in action:
            if "all in" in action:
                raise_from = current_value
                raise_to = 100.9 * bb_stake
            else:
                raise_to = float(action.split('raises ')[1].split(' to ')[0])
                raise_total = float(action.split(' to ')[1])
            return round(raise_to, 5), round(raise_total - raise_to, 5)
        return 0, 0

    def csv_process_poker_hand(self, processed_data):
        columns = [
            'vpip', 'position', 'no_players', 'limp', 'rfi', 'call_rfi', 'three_bet', 'call_three_bet',
            'four_bet', 'call_four_bet', 'five_bet', 'call_five_bet', 'six_bet', 'call_six_bet', 'flop', 'fold',
            'hero_saw_flop', 'hero_is_active_on_flop', 'hero_saw_turn', 'hero_is_active_on_turn',
            'hero_saw_river', 'hero_is_active_on_river',
            'players_see_flop', 'players_see_turn', 'players_see_river',
            'players_active_on_flop', 'players_active_on_turn', 'players_active_on_river',
            'bb_stake', 'hand_result', 'hand', 'flop_HU_with_hero', 'turn_HU_with_hero', 'river_HU_with_hero',
            'flop_Position', 'flop_cards', 'flop_pot',
            'flop_OP', 'flop_IP', 'turn_cards', 'turn_pot', 'turn_OP', 'turn_IP', 'river_cards', 'river_pot',
            'river_IP', 'river_OP', 'Raw Hand'
        ]
        hand_actions_data_frame = pd.DataFrame(columns=columns)
        total_hands_processed = 0
        total_earnings_sum = 0.0
        
        for hand in processed_data:
            # Use hand_result directly if available (from new parsing), otherwise parse Summary
            hand_result = None
            vpip = None
            
            # Check for hand_result from new parser first
            if 'hand_result' in hand:
                try:
                    hand_result_val = hand['hand_result']
                    if hand_result_val is not None:
                        hand_result = float(hand_result_val)
                        if hand_result != 0.0:
                            print(f"DEBUG: Found non-zero hand_result={hand_result} in hand dict")
                except (ValueError, TypeError) as e:
                    print(f"DEBUG: Error converting hand_result: {e}, value={hand_result_val}")
            else:
                print(f"DEBUG: hand_result not in hand dict. Available keys: {list(hand.keys())[:10]}")
            
            # If hand_result not found, try to parse from Summary
            if hand_result is None:
                try:
                    summary = hand.get('Summary', '')
                    if summary:
                        hand_result, vpip = self.process_summary(summary)
                except Exception as e:
                    print(f"Error parsing summary: {e}")
                    hand_result = 0.0
                    vpip = False
            
            # If still None, default to 0
            if hand_result is None:
                hand_result = 0.0
                print(f"DEBUG: hand_result is None, defaulting to 0.0. Summary available: {'Summary' in hand}")
            
            total_hands_processed += 1
            total_earnings_sum += hand_result
            if total_hands_processed <= 5:  # Debug first 5 hands
                print(f"DEBUG: Hand {total_hands_processed} - hand_result={hand_result}, has_Summary={'Summary' in hand}")
            
            # For VPIP, prioritize HandHistory value (most reliable), then process_summary, then determine from actions
            vpip_from_summary = vpip  # Save vpip from process_summary if available
            vpip_from_handhistory = None
            
            # FIRST: Check if HandHistory already calculated vpip (most reliable - position-aware logic)
            if 'vpip' in hand and hand['vpip'] is not None:
                vpip_from_handhistory = bool(hand['vpip'])
                # Use HandHistory value as the source of truth
                vpip = vpip_from_handhistory
                vpip_from_summary = vpip_from_handhistory
            elif vpip is None:
                # Will be determined later from actions
                vpip = False
            
            hand_data = {
                "hand_result": hand_result,
                "vpip": vpip,  # Use HandHistory vpip if available, otherwise from process_summary
                "position": hand.get('Hero Position', hand.get('position', '')),
                "no_players": hand.get('Number Players', hand.get('no_players', 6)),
                "bb_stake": hand.get('BB Stake', hand.get('bb_stake', 0.0)),
                "hand": [card.strip() for card in hand.get('Hand', '[]').split("[")[1].split("]")[0].strip().split(",")] if '[' in hand.get('Hand', '') else [],
                "flop": hand.get('Flop', hand.get('flop', False)),
                "hero_saw_flop": hand.get('hero_saw_flop', False),
                "hero_is_active_on_flop": hand.get('hero_is_active_on_flop', False),
                "hero_saw_turn": hand.get('hero_saw_turn', False),
                "hero_is_active_on_turn": hand.get('hero_is_active_on_turn', False),
                "hero_saw_river": hand.get('hero_saw_river', False),
                "hero_is_active_on_river": hand.get('hero_is_active_on_river', False),
                "players_see_flop": hand.get('players_see_flop', 0),
                "players_see_turn": hand.get('players_see_turn', 0),
                "players_see_river": hand.get('players_see_river', 0),
                "players_active_on_flop": hand.get('players_active_on_flop', []),
                "players_active_on_turn": hand.get('players_active_on_turn', []),
                "players_active_on_river": hand.get('players_active_on_river', []),
                "flop_HU_with_hero": hand.get('HU_hero_flop', hand.get('flop_HU_with_hero', False)),
                "turn_HU_with_hero": hand.get('HU_hero_turn', hand.get('turn_HU_with_hero', False)),
                "river_HU_with_hero": hand.get('HU_hero_river', hand.get('river_HU_with_hero', False)),
                "Raw Hand": hand.get('Raw Hand', '')  # Add raw hand history
            }
            # Always process actions to determine VPIP correctly
            # Pass vpip=True so action_process_summary processes all actions
            action_summary = hand.get('Action Summary', '') or ''
            action_data, pot_size = self.action_process_summary(True, hand['BB Stake'], hand['SB Stake'], hand['Hero Position'], action_summary)
            hand_data.update(action_data)
            post_flop_action_data = self.post_action_process_summary(hand['HU_hero_flop'], hand['Post Flop Action'], hand['BB Stake'], pot_size)
            hand_data.update(post_flop_action_data)

            if 'fold' not in hand_data:
                hand_data['fold'] = 0
            
            # VPIP is already set from HandHistory if available - only use fallback if HandHistory didn't provide it
            if vpip_from_handhistory is None:
                # HandHistory didn't provide vpip, use fallback logic
                # Check action_data for voluntary actions
                voluntary_actions = ['limp', 'rfi', 'call_rfi', 'three_bet', 'call_three_bet', 
                                    'four_bet', 'call_four_bet', 'five_bet', 'call_five_bet', 
                                    'six_bet', 'call_six_bet']
                has_voluntary_action = any(hand_data.get(key, 0) != 0 for key in voluntary_actions)
                
                # Fallback: If Action Summary didn't detect actions, check raw hand data
                if not has_voluntary_action and hand_data.get('Raw Hand'):
                    raw_hand = hand_data['Raw Hand']
                    preflop_section = raw_hand.split('** Dealing Flop **')[0] if '** Dealing Flop **' in raw_hand else raw_hand
                    hero_action_patterns = [
                        r'Hero\s+calls',
                        r'Hero\s+raises',
                        r'Hero\s+bets',
                        r'Hero\s+limps'
                    ]
                    has_other_action = any(re.search(pattern, preflop_section, re.IGNORECASE) for pattern in hero_action_patterns)
                    if has_other_action:
                        has_voluntary_action = True
                
                # Additional check: If vpip_from_summary is True, trust it
                if vpip_from_summary is True:
                    has_voluntary_action = True
                
                # Final fallback: Non-zero result check
                if not has_voluntary_action:
                    hand_result_val = hand_data.get('hand_result', 0)
                    position = hand_data.get('position', '')
                    bb_stake = hand_data.get('bb_stake', 0)
                    
                    if hand_result_val != 0:
                        if position != 'BB':
                            has_voluntary_action = True
                        elif bb_stake > 0 and abs(hand_result_val) > bb_stake * 0.1:
                            has_voluntary_action = True
                
                # Set VPIP based on fallback logic
                if has_voluntary_action:
                    hand_data['vpip'] = True
                else:
                    hand_data['vpip'] = False
            # If HandHistory provided vpip, it's already set correctly in hand_data - don't override
                
            hand_actions_data_frame = pd.concat([hand_actions_data_frame, pd.DataFrame([hand_data])], ignore_index=True)

        # Debug: Check final dataframe
        if len(hand_actions_data_frame) > 0:
            df_earnings_sum = hand_actions_data_frame['hand_result'].sum()
            non_zero_count = (hand_actions_data_frame['hand_result'] != 0).sum()
            print(f"DEBUG: Processed {total_hands_processed} hands")
            print(f"DEBUG: Total earnings from hand dicts: {total_earnings_sum}")
            print(f"DEBUG: Total earnings in dataframe: {df_earnings_sum}")
            print(f"DEBUG: Non-zero hand_result count: {non_zero_count}/{len(hand_actions_data_frame)}")
            if non_zero_count == 0:
                print(f"DEBUG: Sample hand_result values: {hand_actions_data_frame['hand_result'].head(10).tolist()}")
        
        return hand_actions_data_frame

    def flop_HU_with_hero(self, hand):
        turn_hu = False
        river_hu = False

        try:
            flop_index = hand.index("** Dealing Flop **")
            summary_index = hand.index("** Summary **")
            flop_to_summary_lines = hand[flop_index + len("** Dealing Flop **"):summary_index].strip().split('\n')
        except ValueError:
            return False, turn_hu, river_hu, 0

        players = set()
        for line in flop_to_summary_lines:
            match = re.match(r'^[A-Za-z0-9_]+', line)
            if match:
                player = match.group()
                if player not in ['**', 'Dealing', '']:
                    players.add(player)
        if "Hero" in players and len(players) == 2:
            post_flop_action = "\n".join(flop_to_summary_lines)
            if any('Dealing Turn' in line for line in flop_to_summary_lines):
                turn_hu = True
                if any('** Dealing River **' in line for line in flop_to_summary_lines):
                    river_hu = True

            return True, turn_hu, river_hu, post_flop_action
        return False, turn_hu, river_hu, 0





    def parse_hand_header(self, hand: str) -> Dict[str, Any]:
        """Parse hand header to extract metadata"""
        header_data = {}
        
        # Extract hand ID
        hand_id_match = re.search(r'\*\*\*\*\* Hand History For Game (\S+)', hand)
        if hand_id_match:
            header_data['hand_id'] = hand_id_match.group(1)
        else:
            header_data['hand_id'] = "unknown"
        
        # Extract timestamp
        timestamp_match = re.search(r'(\w{3} \d{1,2} \d{2}:\d{2}:\d{2} \w{3} \d{4})', hand)
        if timestamp_match:
            try:
                header_data['timestamp'] = datetime.strptime(timestamp_match.group(1), '%a %d %H:%M:%S %Z %Y')
            except:
                header_data['timestamp'] = None
        else:
            header_data['timestamp'] = None
        
        # Extract stakes
        stakes_match = re.search(r'(\d+\.\d+)/(\d+\.\d+)', hand)
        if stakes_match:
            header_data['stakes_sb'] = float(stakes_match.group(1))
            header_data['stakes_bb'] = float(stakes_match.group(2))
        else:
            header_data['stakes_sb'] = 0.0
            header_data['stakes_bb'] = 0.0
        
        # Extract table name
        table_match = re.search(r'Table (\S+)', hand)
        if table_match:
            header_data['table_name'] = table_match.group(1)
        else:
            header_data['table_name'] = ""
        
        # Extract game type and limit
        if 'Texas Holdem' in hand:
            header_data['game_type'] = "Texas Hold'em"
        else:
            header_data['game_type'] = "Unknown"
        
        if '(NL)' in hand:
            header_data['limit_type'] = "NL"
        elif '(FL)' in hand:
            header_data['limit_type'] = "FL"
        else:
            header_data['limit_type'] = "NL"
        
        # Extract currency (assume USD for now, can be enhanced)
        header_data['currency'] = "USD"
        
        # Extract max players and players dealt in
        max_players_match = re.search(r'Total number of players\s*:\s*(\d+)/(\d+)', hand)
        if max_players_match:
            header_data['players_dealt_in'] = int(max_players_match.group(1))
            header_data['max_players'] = int(max_players_match.group(2))
        else:
            header_data['players_dealt_in'] = 6
            header_data['max_players'] = 6
        
        # Extract button seat
        button_match = re.search(r'Seat (\d+) is the button', hand)
        if button_match:
            header_data['button_seat'] = int(button_match.group(1))
        else:
            header_data['button_seat'] = None
        
        # Store raw header line
        lines = hand.split('\n')
        if len(lines) > 1:
            header_data['raw_header_line'] = lines[1].strip()
        else:
            header_data['raw_header_line'] = ""
        
        return header_data
    
    def parse_seat_information(self, hand: str) -> List[SeatInfo]:
        """Parse seat information from hand history"""
        seats = []
        seat_pattern = r'Seat (\d+):\s*(\S+)\s*\(\$([\d.]+)\)'
        
        for match in re.finditer(seat_pattern, hand):
            seat_num = int(match.group(1))
            player_name = match.group(2)
            starting_stack = float(match.group(3))
            is_hero = (player_name == "Hero")
            
            seats.append(SeatInfo(
                seat_number=seat_num,
                player_name=player_name,
                starting_stack=starting_stack,
                is_hero=is_hero
            ))
        
        return seats
    
    def parse_hero_hole_cards(self, hand: str) -> tuple:
        """Parse Hero's hole cards"""
        hero_cards_match = re.search(r'Dealt to Hero\s*\[\s*(\S+)\s*,\s*(\S+)\s*\]', hand)
        if hero_cards_match:
            card1 = hero_cards_match.group(1).strip()
            card2 = hero_cards_match.group(2).strip()
            return card1, card2
        return None, None
    
    def parse_board_cards(self, hand: str) -> Dict[str, Any]:
        """Parse board cards from hand history"""
        board_data = {
            'flop_card_1': None,
            'flop_card_2': None,
            'flop_card_3': None,
            'turn_card': None,
            'river_card': None,
            'board_flop': [],
            'board_turn': [],
            'board_river': [],
            'board_all': []
        }
        
        # Try to get board from summary first (most reliable)
        summary_match = re.search(r'Board:\s*\[([^\]]+)\]', hand)
        if summary_match:
            board_str = summary_match.group(1)
            board_cards = [c.strip() for c in board_str.split(',') if c.strip()]
            if len(board_cards) >= 3:
                board_data['flop_card_1'] = board_cards[0]
                board_data['flop_card_2'] = board_cards[1]
                board_data['flop_card_3'] = board_cards[2]
                board_data['board_flop'] = board_cards[:3]
                if len(board_cards) >= 4:
                    board_data['turn_card'] = board_cards[3]
                    board_data['board_turn'] = [board_cards[3]]
                if len(board_cards) >= 5:
                    board_data['river_card'] = board_cards[4]
                    board_data['board_river'] = [board_cards[4]]
                board_data['board_all'] = board_cards[:5]
        
        # Also try to parse from individual street markers
        if not board_data['flop_card_1']:
            flop_match = re.search(r'\*\* Dealing Flop \*\*\s*:\s*\[\s*(\S+)\s*,\s*(\S+)\s*,\s*(\S+)\s*\]', hand)
            if flop_match:
                board_data['flop_card_1'] = flop_match.group(1).strip()
                board_data['flop_card_2'] = flop_match.group(2).strip()
                board_data['flop_card_3'] = flop_match.group(3).strip()
                board_data['board_flop'] = [board_data['flop_card_1'], board_data['flop_card_2'], board_data['flop_card_3']]
        
        if not board_data['turn_card']:
            turn_match = re.search(r'\*\* Dealing Turn \*\*\s*:\s*\[\s*(\S+)\s*\]', hand)
            if turn_match:
                board_data['turn_card'] = turn_match.group(1).strip()
                board_data['board_turn'] = [board_data['turn_card']]
        
        if not board_data['river_card']:
            river_match = re.search(r'\*\* Dealing River \*\*\s*:\s*\[\s*(\S+)\s*\]', hand)
            if river_match:
                board_data['river_card'] = river_match.group(1).strip()
                board_data['board_river'] = [board_data['river_card']]
        
        # Build board_all if we have all cards
        if board_data['flop_card_1'] and board_data['flop_card_2'] and board_data['flop_card_3']:
            board_data['board_all'] = [
                board_data['flop_card_1'],
                board_data['flop_card_2'],
                board_data['flop_card_3']
            ]
            if board_data['turn_card']:
                board_data['board_all'].append(board_data['turn_card'])
            if board_data['river_card']:
                board_data['board_all'].append(board_data['river_card'])
        
        return board_data
    
    def parse_actions(self, hand: str, stakes_sb: float, stakes_bb: float) -> List[Action]:
        """Parse all actions across all streets with full context"""
        actions = []
        action_index = 0
        
        # Track pot and stacks as we go
        pot = 0.0
        stacks = {}  # player_name -> current_stack
        
        # Initialize stacks from seat info
        seats = self.parse_seat_information(hand)
        for seat in seats:
            stacks[seat.player_name] = seat.starting_stack
        
        # Split hand into sections
        sections = []
        if '** Dealing down cards **' in hand:
            preflop_section = hand.split('** Dealing down cards **')[1]
            if '** Dealing Flop **' in preflop_section:
                preflop_text = preflop_section.split('** Dealing Flop **')[0]
                sections.append(('preflop', preflop_text))
                flop_section = preflop_section.split('** Dealing Flop **')[1]
                if '** Dealing Turn **' in flop_section:
                    flop_text = flop_section.split('** Dealing Turn **')[0]
                    sections.append(('flop', flop_text))
                    turn_section = flop_section.split('** Dealing Turn **')[1]
                    if '** Dealing River **' in turn_section:
                        turn_text = turn_section.split('** Dealing River **')[0]
                        sections.append(('turn', turn_text))
                        river_section = turn_section.split('** Dealing River **')[1]
                        if '** Summary **' in river_section:
                            river_text = river_section.split('** Summary **')[0]
                            sections.append(('river', river_text))
                    elif '** Summary **' in turn_section:
                        turn_text = turn_section.split('** Summary **')[0]
                        sections.append(('turn', turn_text))
                elif '** Summary **' in flop_section:
                    flop_text = flop_section.split('** Summary **')[0]
                    sections.append(('flop', flop_text))
            elif '** Summary **' in preflop_section:
                preflop_text = preflop_section.split('** Summary **')[0]
                sections.append(('preflop', preflop_text))
        
        # First, add blind postings as preflop actions
        for line in hand.split('\n'):
            line = line.strip()
            if 'posts small blind' in line:
                match = re.search(r'(\S+)\s+posts small blind\s+\(([\d.]+)\)', line)
                if match:
                    player = match.group(1)
                    amount = float(match.group(2))
                    pot_before = pot
                    pot += amount
                    if player in stacks:
                        stacks[player] -= amount
                    
                    actions.append(Action(
                        street="preflop",
                        action_index=action_index,
                        actor=player,
                        action_type="post_sb",
                        amount=amount,
                        to_call_before=0.0,
                        stack_before=stacks.get(player, 0.0) + amount,
                        stack_after=stacks.get(player, 0.0),
                        pot_before=pot_before,
                        pot_after=pot,
                        is_all_in=False
                    ))
                    action_index += 1
            
            elif 'posts big blind' in line:
                match = re.search(r'(\S+)\s+posts big blind\s+\(([\d.]+)\)', line)
                if match:
                    player = match.group(1)
                    amount = float(match.group(2))
                    pot_before = pot
                    pot += amount
                    if player in stacks:
                        stacks[player] -= amount
                    
                    actions.append(Action(
                        street="preflop",
                        action_index=action_index,
                        actor=player,
                        action_type="post_bb",
                        amount=amount,
                        to_call_before=0.0,
                        stack_before=stacks.get(player, 0.0) + amount,
                        stack_after=stacks.get(player, 0.0),
                        pot_before=pot_before,
                        pot_after=pot,
                        is_all_in=False
                    ))
                    action_index += 1
        
        # Track current bet to call for each street
        current_bet = stakes_bb
        
        # Parse actions for each street
        for street, section_text in sections:
            lines = section_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                action = None
                pot_before = pot
                to_call_before = current_bet
                
                # Parse different action types
                if 'folds' in line.lower():
                    match = re.search(r'(\S+)\s+folds', line, re.IGNORECASE)
                    if match:
                        player = match.group(1)
                        action = Action(
                            street=street,
                            action_index=action_index,
                            actor=player,
                            action_type="fold",
                            amount=0.0,
                            to_call_before=to_call_before,
                            stack_before=stacks.get(player, 0.0),
                            stack_after=stacks.get(player, 0.0),
                            pot_before=pot_before,
                            pot_after=pot,
                            is_all_in=False
                        )
                
                elif 'checks' in line.lower():
                    match = re.search(r'(\S+)\s+checks', line, re.IGNORECASE)
                    if match:
                        player = match.group(1)
                        action = Action(
                            street=street,
                            action_index=action_index,
                            actor=player,
                            action_type="check",
                            amount=0.0,
                            to_call_before=0.0,
                            stack_before=stacks.get(player, 0.0),
                            stack_after=stacks.get(player, 0.0),
                            pot_before=pot_before,
                            pot_after=pot,
                            is_all_in=False
                        )
                        current_bet = 0.0  # Reset bet after check
                
                elif 'calls' in line.lower():
                    match = re.search(r'(\S+)\s+calls\s+\(([\d.]+)\)', line, re.IGNORECASE)
                    if match:
                        player = match.group(1)
                        call_amount = float(match.group(2))
                        pot += call_amount
                        if player in stacks:
                            stacks[player] -= call_amount
                        
                        action = Action(
                            street=street,
                            action_index=action_index,
                            actor=player,
                            action_type="call",
                            amount=call_amount,
                            to_call_before=to_call_before,
                            stack_before=stacks.get(player, 0.0) + call_amount,
                            stack_after=stacks.get(player, 0.0),
                            pot_before=pot_before,
                            pot_after=pot,
                            is_all_in=(stacks.get(player, 0.0) == 0.0)
                        )
                
                elif 'bets' in line.lower() and 'raises' not in line.lower():
                    match = re.search(r'(\S+)\s+bets\s+\(([\d.]+)\)', line, re.IGNORECASE)
                    if match:
                        player = match.group(1)
                        bet_amount = float(match.group(2))
                        pot += bet_amount
                        if player in stacks:
                            stacks[player] -= bet_amount
                        
                        bet_size_pct = (bet_amount / pot_before * 100) if pot_before > 0 else 0.0
                        current_bet = bet_amount
                        
                        action = Action(
                            street=street,
                            action_index=action_index,
                            actor=player,
                            action_type="bet",
                            amount=bet_amount,
                            to_call_before=to_call_before,
                            bet_size_total=bet_amount,
                            bet_size_pct_pot=bet_size_pct,
                            stack_before=stacks.get(player, 0.0) + bet_amount,
                            stack_after=stacks.get(player, 0.0),
                            pot_before=pot_before,
                            pot_after=pot,
                            is_all_in=(stacks.get(player, 0.0) == 0.0)
                        )
                
                elif 'raises' in line.lower():
                    # Parse raise: "Player raises X to Y" or "Player raises X to Y (all in)"
                    match = re.search(r'(\S+)\s+raises\s+([\d.]+)\s+to\s+([\d.]+)', line, re.IGNORECASE)
                    if match:
                        player = match.group(1)
                        raise_amount = float(match.group(2))
                        raise_to = float(match.group(3))
                        
                        # Calculate how much new money goes in
                        # If player already had current_bet in, they need to add (raise_to - current_bet)
                        # For simplicity, use raise_amount as the new money
                        new_money = raise_to - current_bet if current_bet > 0 else raise_to
                        pot += new_money
                        if player in stacks:
                            stacks[player] -= new_money
                        
                        bet_size_pct = (new_money / pot_before * 100) if pot_before > 0 else 0.0
                        current_bet = raise_to
                        is_all_in = 'all in' in line.lower() or (stacks.get(player, 0.0) == 0.0)
                        
                        action = Action(
                            street=street,
                            action_index=action_index,
                            actor=player,
                            action_type="all_in" if is_all_in else "raise",
                            amount=new_money,
                            to_call_before=to_call_before,
                            bet_size_total=raise_to,
                            bet_size_pct_pot=bet_size_pct,
                            stack_before=stacks.get(player, 0.0) + new_money,
                            stack_after=stacks.get(player, 0.0),
                            pot_before=pot_before,
                            pot_after=pot,
                            is_all_in=is_all_in
                        )
                
                if action:
                    actions.append(action)
                    action_index += 1
        
        return actions
    
    def parse_summary(self, hand: str) -> Dict[str, Any]:
        """Parse summary section for final pot, rake, and player results"""
        summary_data = {
            'final_pot': 0.0,
            'rake': 0.0,
            'board_final': [],
            'side_pots': [],
            'player_results': []
        }
        
        if '** Summary **' not in hand:
            return summary_data
        
        summary_section = hand.split('** Summary **')[1]
        
        # Extract main pot
        pot_match = re.search(r'Main Pot:\s*\$?([\d.]+)', summary_section)
        if pot_match:
            summary_data['final_pot'] = float(pot_match.group(1))
        
        # Extract rake
        rake_match = re.search(r'Rake:\s*\$?([\d.]+)', summary_section)
        if rake_match:
            summary_data['rake'] = float(rake_match.group(1))
        
        # Extract board
        board_match = re.search(r'Board:\s*\[([^\]]+)\]', summary_section)
        if board_match:
            board_str = board_match.group(1)
            summary_data['board_final'] = [c.strip() for c in board_str.split(',') if c.strip()]
        
        # Parse each player's result - use multiple simpler patterns to avoid alternation issues
        # Format variations:
        # - "Player balance $X, bet $Y, collected $Z, net +$W[ cards ][ description ]"
        # - "Player balance $X, lost $Y[ cards ][ description ]"
        # - "Player balance $X, lost $Y (folded)"
        # - "Player balance $X, didn't bet (folded)"
        
        # Track processed players to avoid duplicates
        processed_players = set()
        
        # Pattern 1: bet/collected/net pattern - prioritize net amount
        # Match formats:
        # - "Player balance $X, bet $Y, collected $Z, net +$W"
        # - "Player balance $X, net +$W"
        # Make the pattern more flexible - allow bet/collected/net in any combination
        pattern_bet = r'(\S+)\s+balance\s+\$?([\d.]+)(?:,\s*(?:bet\s+\$?([\d.]+),?\s*)?(?:collected\s+\$?([\d.]+),?\s*)?(?:net\s+([+-])\$?([\d.]+))?)?(?:\s*\(folded\))?(?:\s*\[([^\]]+)\])?(?:\s*\[([^\]]+)\])?'
        # Pattern 2: lost pattern
        pattern_lost = r'(\S+)\s+balance\s+\$?([\d.]+),\s*lost\s+\$?([\d.]+)(?:\s*\(folded\))?(?:\s*\[([^\]]+)\])?(?:\s*\[([^\]]+)\])?'
        # Pattern 3: didn't bet pattern
        pattern_didnt_bet = r'(\S+)\s+balance\s+\$?([\d.]+),\s*(didn\'t bet)(?:\s*\(folded\))?(?:\s*\[([^\]]+)\])?(?:\s*\[([^\]]+)\])?'
        
        # Try each pattern - process in order: bet (most specific), lost, didn't bet
        for match in re.finditer(pattern_bet, summary_section):
            try:
                player_name = match.group(1)
                if player_name in processed_players:
                    continue
                processed_players.add(player_name)
                ending_stack = float(match.group(2))
            except (IndexError, AttributeError) as e:
                print(f"Error parsing player result (bet pattern): {e}")
                continue
            
            net_result = 0.0
            amount_contributed = 0.0
            won_pot = False
            showed_down = False
            final_hand_cards = None
            final_hand_description = None
            
            def safe_group(m, group_num):
                try:
                    if m.lastindex is None or group_num > m.lastindex:
                        return None
                    result = m.group(group_num)
                    return result if result else None
                except (IndexError, AttributeError):
                    return None
            
            group3 = safe_group(match, 3)  # bet amount
            group4 = safe_group(match, 4)  # collected amount
            group5 = safe_group(match, 5)  # net sign (+ or -)
            group6 = safe_group(match, 6)  # net amount
            group7 = safe_group(match, 7)  # cards
            group8 = safe_group(match, 8)  # description
            
            # Use net amount directly if available (most accurate)
            if group5 and group6:
                net_value = float(group6)
                if group5 == '-':
                    net_result = -net_value
                else:
                    net_result = net_value
                won_pot = (net_result > 0)
                # Calculate amount_contributed from bet if available
                if group3:
                    amount_contributed = float(group3)
                elif group4:
                    # If no bet amount, use collected - net as contribution
                    collected = float(group4)
                    amount_contributed = collected - net_result
            elif group3 and group4:
                # Fallback: calculate from bet and collected
                amount_contributed = float(group3)
                collected = float(group4)
                net_result = collected - amount_contributed
                won_pot = (collected > amount_contributed)
            elif group3:
                # Only bet amount, no collected (folded after betting)
                amount_contributed = float(group3)
                net_result = -amount_contributed
                won_pot = False
            elif group4:
                # Only collected (won without betting? unlikely but handle it)
                collected = float(group4)
                net_result = collected
                won_pot = True
                amount_contributed = 0.0
            
            if group7:
                showed_down = True
                final_hand_cards = [c.strip() for c in group7.split(',') if c.strip()]
            if group8:
                final_hand_description = group8.strip()
            
            summary_data['player_results'].append(PlayerResult(
                player_name=player_name,
                ending_stack=ending_stack,
                net_result=net_result,
                amount_contributed=amount_contributed,
                won_pot=won_pot,
                showed_down=showed_down,
                final_hand_cards=final_hand_cards,
                final_hand_description=final_hand_description
            ))
        
        # Process lost pattern
        for match in re.finditer(pattern_lost, summary_section):
            try:
                player_name = match.group(1)
                if player_name in processed_players:
                    continue
                processed_players.add(player_name)
                ending_stack = float(match.group(2))
                lost_amount = float(match.group(3))
            except (IndexError, AttributeError) as e:
                print(f"Error parsing player result (lost pattern): {e}")
                continue
            
            def safe_group(m, group_num):
                try:
                    if m.lastindex is None or group_num > m.lastindex:
                        return None
                    result = m.group(group_num)
                    return result if result else None
                except (IndexError, AttributeError):
                    return None
            
            group4 = safe_group(match, 4)  # cards
            group5 = safe_group(match, 5)  # description
            
            final_hand_cards = None
            final_hand_description = None
            if group4:
                showed_down = True
                final_hand_cards = [c.strip() for c in group4.split(',') if c.strip()]
            if group5:
                final_hand_description = group5.strip()
            
            summary_data['player_results'].append(PlayerResult(
                player_name=player_name,
                ending_stack=ending_stack,
                net_result=-lost_amount,
                amount_contributed=lost_amount,
                won_pot=False,
                showed_down=showed_down if group4 else False,
                final_hand_cards=final_hand_cards,
                final_hand_description=final_hand_description
            ))
        
        # Process didn't bet pattern
        for match in re.finditer(pattern_didnt_bet, summary_section):
            try:
                player_name = match.group(1)
                if player_name in processed_players:
                    continue
                processed_players.add(player_name)
                ending_stack = float(match.group(2))
            except (IndexError, AttributeError) as e:
                print(f"Error parsing player result (didn't bet pattern): {e}")
                continue
            
            def safe_group(m, group_num):
                try:
                    if m.lastindex is None or group_num > m.lastindex:
                        return None
                    result = m.group(group_num)
                    return result if result else None
                except (IndexError, AttributeError):
                    return None
            
            group4 = safe_group(match, 4)  # cards
            group5 = safe_group(match, 5)  # description
            
            final_hand_cards = None
            final_hand_description = None
            if group4:
                showed_down = True
                final_hand_cards = [c.strip() for c in group4.split(',') if c.strip()]
            if group5:
                final_hand_description = group5.strip()
            
            summary_data['player_results'].append(PlayerResult(
                player_name=player_name,
                ending_stack=ending_stack,
                net_result=0.0,
                amount_contributed=0.0,
                won_pot=False,
                showed_down=showed_down if group4 else False,
                final_hand_cards=final_hand_cards,
                final_hand_description=final_hand_description
            ))
        
        # Always parse Hero directly as fallback/override (more reliable than regex)
        # Remove any existing Hero result first
        summary_data['player_results'] = [r for r in summary_data['player_results'] if r.player_name != 'Hero']
        hero_found = False
        
        # Now parse Hero line directly
        if True:  # Always run this parser for Hero
            # Try to find Hero line directly - use simpler, more robust parsing
            hero_lines = [line.strip() for line in summary_section.split('\n') if 'Hero' in line and 'balance' in line]
            if not hero_lines:
                print(f"WARNING: No Hero line found in summary section")
                print(f"Summary section preview: {summary_section[:500]}")
            for hero_line in hero_lines:
                print(f"DEBUG: Parsing Hero line: {hero_line[:150]}")
                try:
                    # Extract balance first
                    balance_match = re.search(r'balance\s+\$?([\d.]+)', hero_line)
                    ending_stack = float(balance_match.group(1)) if balance_match else 0.0
                    
                    net_result = 0.0
                    amount_contributed = 0.0
                    won_pot = False
                    showed_down = False
                    final_hand_cards = None
                    final_hand_description = None
                    
                    # Try multiple patterns to extract net result (in order of preference)
                    # Pattern 1: "net +$X" or "net -$X" (most accurate)
                    net_match = re.search(r'net\s+([+-])\$?([\d.]+)', hero_line)
                    if net_match:
                        sign = net_match.group(1)
                        amount = float(net_match.group(2))
                        net_result = amount if sign == '+' else -amount
                        won_pot = (net_result > 0)
                        # Also extract bet amount if available for amount_contributed
                        bet_match = re.search(r'bet\s+\$?([\d.]+)', hero_line)
                        if bet_match:
                            amount_contributed = float(bet_match.group(1))
                    # Pattern 2: "bet $X, collected $Y" (calculate net from these)
                    elif 'bet $' in hero_line and 'collected $' in hero_line:
                        bet_match = re.search(r'bet\s+\$?([\d.]+)', hero_line)
                        collected_match = re.search(r'collected\s+\$?([\d.]+)', hero_line)
                        if bet_match and collected_match:
                            bet_amount = float(bet_match.group(1))
                            collected_amount = float(collected_match.group(1))
                            net_result = collected_amount - bet_amount
                            amount_contributed = bet_amount
                            won_pot = (collected_amount > bet_amount)
                    # Pattern 3: "lost $X"
                    elif 'lost $' in hero_line or ('lost' in hero_line.lower() and '$' in hero_line):
                        lost_match = re.search(r'lost\s+\$?([\d.]+)', hero_line)
                        if lost_match:
                            lost_amount = float(lost_match.group(1))
                            net_result = -lost_amount
                            amount_contributed = lost_amount
                            won_pot = False
                    # Pattern 4: "didn't bet" = 0
                    elif "didn't bet" in hero_line.lower():
                        net_result = 0.0
                        won_pot = False
                        amount_contributed = 0.0
                    
                    # Extract cards and description if present
                    cards_match = re.search(r'\[([^\]]+)\]', hero_line)
                    if cards_match:
                        showed_down = True
                        cards_str = cards_match.group(1)
                        final_hand_cards = [c.strip() for c in cards_str.split(',') if c.strip()]
                    
                    # Always add Hero if we found a Hero line (even if net_result is 0)
                    # This ensures Hero is always in player_results
                    print(f"DEBUG: Hero parsed - net_result={net_result}, ending_stack={ending_stack}")
                    summary_data['player_results'].append(PlayerResult(
                        player_name='Hero',
                        ending_stack=ending_stack,
                        net_result=net_result,
                        amount_contributed=amount_contributed,
                        won_pot=won_pot,
                        showed_down=showed_down,
                        final_hand_cards=final_hand_cards,
                        final_hand_description=final_hand_description
                    ))
                    hero_found = True
                    # Debug output
                    if net_result == 0.0 and "didn't bet" not in hero_line.lower():
                        print(f"WARNING: Hero line parsed but net_result is 0: {hero_line[:100]}")
                        print(f"  Pattern 1 (net): {bool(re.search(r'net\s+([+-])\$?([\d.]+)', hero_line))}")
                        print(f"  Pattern 2 (bet/collected): {bool('bet $' in hero_line and 'collected $' in hero_line)}")
                        print(f"  Pattern 3 (lost): {bool('lost $' in hero_line or ('lost' in hero_line.lower() and '$' in hero_line))}")
                        print(f'  Pattern 4 (didn\'t bet): {bool("didn\'t bet" in hero_line.lower())}')
                    break
                except (ValueError, AttributeError, IndexError) as e:
                    print(f"Error parsing Hero line '{hero_line}': {e}")
                    continue
        
        return summary_data
    
    def calculate_hero_position(self, hand_history: HandHistory) -> str:
        """Calculate Hero's absolute position for 3-6 handed tables"""
        if not hand_history.button_seat or not hand_history.seats:
            return None
        
        # Find Hero's seat
        hero_seat = None
        for seat in hand_history.seats:
            if seat.is_hero:
                hero_seat = seat.seat_number
                break
        
        if not hero_seat:
            return None
        
        # Get seat order (sorted by seat number)
        sorted_seats = sorted(hand_history.seats, key=lambda s: s.seat_number)
        button_index = None
        hero_index = None
        
        for i, seat in enumerate(sorted_seats):
            if seat.seat_number == hand_history.button_seat:
                button_index = i
            if seat.seat_number == hero_seat:
                hero_index = i
        
        if button_index is None or hero_index is None:
            return None
        
        # Position names based on table size (working backwards from BB)
        players_dealt = hand_history.players_dealt_in
        if players_dealt == 2:
            positions = ['SB', 'BB']
        elif players_dealt == 3:
            positions = ['BTN', 'SB', 'BB']
        elif players_dealt == 4:
            positions = ['CO', 'BTN', 'SB', 'BB']
        elif players_dealt == 5:
            positions = ['MP', 'CO', 'BTN', 'SB', 'BB']
        else:  # 6 handed
            positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        
        # Calculate position relative to button
        # In poker, action order is: UTG -> MP -> CO -> BTN -> SB -> BB
        # For 6-handed: UTG is first to act (3 positions clockwise from button)
        # Calculate offset: how many seats clockwise from button to hero
        # In sorted seats, if button_index < hero_index, offset is positive
        # If button_index > hero_index, we need to wrap around
        offset_from_button = (hero_index - button_index) % players_dealt
        
        # For 6-handed: positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        # Action order relative to button:
        #   offset 0 -> BTN (at button, index 3 in array)
        #   offset 1 -> SB (1 seat clockwise, index 4)
        #   offset 2 -> BB (2 seats clockwise, index 5)
        #   offset 3 -> UTG (3 seats clockwise, index 0) - FIRST TO ACT
        #   offset 4 -> MP (4 seats clockwise, index 1)
        #   offset 5 -> CO (5 seats clockwise, index 2)
        
        # BTN index in positions array depends on table size:
        #   2-handed: positions = ['SB', 'BB'] - no BTN, button is at SB (index 0)
        #   3-handed: positions = ['BTN', 'SB', 'BB'] - BTN at index 0
        #   4-handed: positions = ['CO', 'BTN', 'SB', 'BB'] - BTN at index 1
        #   5-handed: positions = ['MP', 'CO', 'BTN', 'SB', 'BB'] - BTN at index 2
        #   6-handed: positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB'] - BTN at index 3
        # Formula: 
        #   - 2-handed: button is SB (index 0)
        #   - 3-handed: button is BTN (index 0)
        #   - 4+ handed: button is BTN at index (players_dealt - 3)
        if players_dealt == 2:
            btn_index_in_positions = 0  # Button is at SB
        elif players_dealt == 3:
            btn_index_in_positions = 0  # Button is at BTN
        else:
            btn_index_in_positions = players_dealt - 3  # BTN position index
        
        # Map offset to position index: add offset to button index, wrap around
        position_index = (btn_index_in_positions + offset_from_button) % len(positions)
        
        calculated_position = positions[position_index]
        
        return calculated_position
    
    def calculate_preflop_roles(self, hand_history: HandHistory) -> Dict[str, Any]:
        """Calculate Hero's preflop role and opportunities"""
        roles = {
            'opened_pot': False,
            'limped': False,
            'had_3bet_opportunity': False,
            'did_3bet': False,
            'had_4bet_opportunity': False,
            'did_4bet': False,
            'faced_open_raise': False,
            'faced_3bet': False,
            'faced_4bet': False,
            'preflop_role': None,
            'preflop_aggressor': None
        }
        
        preflop_actions = [a for a in hand_history.actions if a.street == 'preflop']
        if not preflop_actions:
            return roles
        
        # Track raise levels
        raise_levels = []  # List of (player, raise_to_amount)
        hero_actions = [a for a in preflop_actions if a.actor == 'Hero']
        
        # Find first raise (open raise)
        first_raise = None
        for action in preflop_actions:
            if action.action_type in ['bet', 'raise', 'all_in'] and action.actor != 'Hero':
                first_raise = action
                roles['faced_open_raise'] = True
                break
        
        # Check if Hero limped
        for action in hero_actions:
            if action.action_type == 'call' and action.to_call_before == hand_history.stakes_bb:
                # Called BB without raising = limp
                roles['limped'] = True
                break
        
        # Check if Hero opened (first raiser)
        hero_first_raise = None
        for action in preflop_actions:
            if action.action_type in ['bet', 'raise', 'all_in']:
                if action.actor == 'Hero':
                    hero_first_raise = action
                    roles['opened_pot'] = True
                    break
                else:
                    break  # Someone else raised first
        
        # Track all raises to determine 3-bet, 4-bet opportunities
        raises = []
        for action in preflop_actions:
            if action.action_type in ['bet', 'raise', 'all_in']:
                raises.append((action.actor, action.bet_size_total or action.amount))
        
        # Determine preflop aggressor (last person to make biggest raise)
        if raises:
            roles['preflop_aggressor'] = raises[-1][0]
        
        # Check for 3-bet, 4-bet opportunities and actions
        if len(raises) >= 1:
            # There was at least one raise
            if len(raises) >= 2:
                # There was a 3-bet
                roles['faced_3bet'] = True
                if len(raises) >= 3:
                    roles['faced_4bet'] = True
                
                # Check if Hero had opportunity to 3-bet or 4-bet
                hero_raise_indices = [i for i, (player, _) in enumerate(raises) if player == 'Hero']
                if hero_raise_indices:
                    hero_last_raise_idx = hero_raise_indices[-1]
                    if hero_last_raise_idx == 1:  # Hero made the 3-bet
                        roles['did_3bet'] = True
                    elif hero_last_raise_idx == 2:  # Hero made the 4-bet
                        roles['did_4bet'] = True
                else:
                    # Hero didn't raise, check if they had opportunity
                    if len(raises) >= 1 and not any(p == 'Hero' for p, _ in raises[:1]):
                        roles['had_3bet_opportunity'] = True
                    if len(raises) >= 2 and not any(p == 'Hero' for p, _ in raises[:2]):
                        roles['had_4bet_opportunity'] = True
        
        # Determine Hero's role
        if roles['did_4bet']:
            roles['preflop_role'] = '4_bettor'
        elif roles['did_3bet']:
            # Check if it's a squeeze (3-bet after raise + callers)
            # Need to check if there were callers before Hero's 3-bet
            hero_3bet_action = None
            for action in preflop_actions:
                if action.actor == 'Hero' and action.action_type in ['raise', 'all_in']:
                    hero_3bet_action = action
                    break
            
            if hero_3bet_action:
                # Check for callers before Hero's 3-bet
                callers_before = False
                for action in preflop_actions:
                    if action.action_index >= hero_3bet_action.action_index:
                        break
                    if action.action_type == 'call' and action.actor != 'Hero':
                        callers_before = True
                        break
                
                if callers_before:
                    roles['preflop_role'] = 'squeezer'
                else:
                    roles['preflop_role'] = '3_bettor'
        elif roles['opened_pot']:
            # Check if it's an ISO raise (raise after limpers)
            limpers_before = False
            for action in preflop_actions:
                if action.actor == 'Hero':
                    break
                if action.action_type == 'call' and action.to_call_before == hand_history.stakes_bb:
                    limpers_before = True
                    break
            
            if limpers_before:
                roles['preflop_role'] = 'iso_raiser'
            else:
                roles['preflop_role'] = 'open_raiser'
        elif roles['faced_open_raise']:
            # Check if Hero called
            hero_called = any(a.action_type == 'call' and a.actor == 'Hero' for a in preflop_actions)
            if hero_called:
                roles['preflop_role'] = 'cold_caller'
        elif roles['faced_3bet']:
            # Check if Hero called the 3-bet
            hero_called_3bet = False
            for action in preflop_actions:
                if action.actor == 'Hero' and action.action_type == 'call':
                    # Check if this call was facing a 3-bet
                    # (simplified - would need to track raise levels more precisely)
                    hero_called_3bet = True
                    break
            if hero_called_3bet:
                roles['preflop_role'] = 'caller_vs_3bet'
        
        return roles
    
    def calculate_street_metrics(self, hand_history: HandHistory) -> Dict[str, Any]:
        """Calculate postflop metrics for each street"""
        metrics = {}
        
        # Get active players for each street
        for street in ['flop', 'turn', 'river']:
            street_actions = [a for a in hand_history.actions if a.street == street]
            
            if not street_actions:
                # No actions on this street means no one saw it
                metrics[f'players_see_{street}'] = 0
                metrics[f'hero_saw_{street}'] = False
                metrics[f'players_active_on_{street}'] = []
                metrics[f'hero_is_active_on_{street}'] = False
                metrics[f'hero_action_order_index_{street}'] = None
                metrics[f'hero_action_order_count_{street}'] = None
                metrics[f'hero_relative_position_category_{street}'] = None
                metrics[f'hero_position_vs_preflop_raiser_{street}'] = None
                continue
            
            # Get players who acted on this street (they saw it)
            players_who_acted = set()
            for action in street_actions:
                if action.action_type != 'fold':  # Folds don't count as "seeing" the street
                    players_who_acted.add(action.actor)
            
            metrics[f'players_see_{street}'] = len(players_who_acted)
            metrics[f'hero_saw_{street}'] = 'Hero' in players_who_acted
            
            # Get players active at start of street (before any folds)
            # This is players who had an action opportunity
            active_players = set()
            for action in street_actions:
                active_players.add(action.actor)
            
            active_players_list = list(active_players)
            metrics[f'players_active_on_{street}'] = active_players_list
            metrics[f'hero_is_active_on_{street}'] = 'Hero' in active_players_list
            
            if 'Hero' in active_players_list:
                # Find Hero's action order
                hero_first_action = None
                for action in street_actions:
                    if action.actor == 'Hero':
                        hero_first_action = action
                        break
                
                if hero_first_action:
                    # Count how many players acted before Hero
                    players_before_hero = set()
                    for action in street_actions:
                        if action.action_index < hero_first_action.action_index:
                            players_before_hero.add(action.actor)
                    
                    hero_index = len(players_before_hero)
                    total_players = len(active_players_list)
                    
                    metrics[f'hero_action_order_index_{street}'] = hero_index
                    metrics[f'hero_action_order_count_{street}'] = total_players
                    
                    # Determine position category
                    if hero_index == 0:
                        category = 'first_to_act'
                        position_vs = 'OOP'
                    elif hero_index == total_players - 1:
                        category = 'last_to_act'
                        position_vs = 'IP'
                    else:
                        category = 'MP'
                        position_vs = 'MP'
                    
                    metrics[f'hero_relative_position_category_{street}'] = category
                    metrics[f'hero_position_vs_preflop_raiser_{street}'] = position_vs
                else:
                    metrics[f'hero_action_order_index_{street}'] = None
                    metrics[f'hero_action_order_count_{street}'] = None
                    metrics[f'hero_relative_position_category_{street}'] = None
                    metrics[f'hero_position_vs_preflop_raiser_{street}'] = None
            else:
                metrics[f'hero_action_order_index_{street}'] = None
                metrics[f'hero_action_order_count_{street}'] = None
                metrics[f'hero_relative_position_category_{street}'] = None
                metrics[f'hero_position_vs_preflop_raiser_{street}'] = None
        
        return metrics
    
    def parse_hand_to_history(self, hand: str) -> Optional[HandHistory]:
        """Parse a single hand into a HandHistory object"""
        try:
            if "Hero" not in hand:
                return None
            
            # Parse header
            header_data = self.parse_hand_header(hand)
            
            # Parse seats
            seats = self.parse_seat_information(hand)
            
            # Parse hero cards
            hero_card_1, hero_card_2 = self.parse_hero_hole_cards(hand)
            
            # Parse board
            board_data = self.parse_board_cards(hand)
            
            # Parse actions
            actions = self.parse_actions(hand, header_data['stakes_sb'], header_data['stakes_bb'])
            
            # Parse summary
            summary_data = self.parse_summary(hand)
            
            # Create HandHistory object
            hand_history = HandHistory(
                hand_id=header_data['hand_id'],
                site=header_data.get('site', 'LabWorks'),
                table_name=header_data['table_name'],
                stakes_sb=header_data['stakes_sb'],
                stakes_bb=header_data['stakes_bb'],
                currency=header_data['currency'],
                game_type=header_data['game_type'],
                limit_type=header_data['limit_type'],
                max_players=header_data['max_players'],
                players_dealt_in=header_data['players_dealt_in'],
                button_seat=header_data['button_seat'],
                timestamp=header_data['timestamp'],
                raw_header_line=header_data['raw_header_line'],
                seats=seats,
                hero_hole_card_1=hero_card_1,
                hero_hole_card_2=hero_card_2,
                flop_card_1=board_data['flop_card_1'],
                flop_card_2=board_data['flop_card_2'],
                flop_card_3=board_data['flop_card_3'],
                turn_card=board_data['turn_card'],
                river_card=board_data['river_card'],
                board_flop=board_data['board_flop'],
                board_turn=board_data['board_turn'],
                board_river=board_data['board_river'],
                board_all=board_data['board_all'],
                actions=actions,
                final_pot=summary_data['final_pot'],
                rake=summary_data['rake'],
                board_final=summary_data['board_final'],
                side_pots=summary_data['side_pots'],
                player_results=summary_data['player_results'],
                raw_hand=hand
            )
            
            # Calculate derived fields
            hand_history.hero_preflop_absolute_position = self.calculate_hero_position(hand_history)
            
            # Calculate preflop roles
            preflop_roles = self.calculate_preflop_roles(hand_history)
            hand_history.opened_pot = preflop_roles['opened_pot']
            hand_history.limped = preflop_roles['limped']
            hand_history.had_3bet_opportunity = preflop_roles['had_3bet_opportunity']
            hand_history.did_3bet = preflop_roles['did_3bet']
            hand_history.had_4bet_opportunity = preflop_roles['had_4bet_opportunity']
            hand_history.did_4bet = preflop_roles['did_4bet']
            hand_history.faced_open_raise = preflop_roles['faced_open_raise']
            hand_history.faced_3bet = preflop_roles['faced_3bet']
            hand_history.faced_4bet = preflop_roles['faced_4bet']
            hand_history.preflop_role = preflop_roles['preflop_role']
            hand_history.preflop_aggressor = preflop_roles['preflop_aggressor']
            
            # Calculate street metrics
            street_metrics = self.calculate_street_metrics(hand_history)
            hand_history.table_size_at_start = hand_history.max_players
            hand_history.players_see_flop = street_metrics.get('players_see_flop', 0)
            hand_history.players_see_turn = street_metrics.get('players_see_turn', 0)
            hand_history.players_see_river = street_metrics.get('players_see_river', 0)
            hand_history.hero_saw_flop = street_metrics.get('hero_saw_flop', False)
            hand_history.hero_saw_turn = street_metrics.get('hero_saw_turn', False)
            hand_history.hero_saw_river = street_metrics.get('hero_saw_river', False)
            hand_history.players_active_on_flop = street_metrics.get('players_active_on_flop', [])
            hand_history.players_active_on_turn = street_metrics.get('players_active_on_turn', [])
            hand_history.players_active_on_river = street_metrics.get('players_active_on_river', [])
            hand_history.hero_is_active_on_flop = street_metrics.get('hero_is_active_on_flop', False)
            hand_history.hero_is_active_on_turn = street_metrics.get('hero_is_active_on_turn', False)
            hand_history.hero_is_active_on_river = street_metrics.get('hero_is_active_on_river', False)
            hand_history.hero_action_order_index_flop = street_metrics.get('hero_action_order_index_flop')
            hand_history.hero_action_order_count_flop = street_metrics.get('hero_action_order_count_flop')
            hand_history.hero_relative_position_category_flop = street_metrics.get('hero_relative_position_category_flop')
            hand_history.hero_position_vs_preflop_raiser_flop = street_metrics.get('hero_position_vs_preflop_raiser_flop')
            hand_history.hero_action_order_index_turn = street_metrics.get('hero_action_order_index_turn')
            hand_history.hero_action_order_count_turn = street_metrics.get('hero_action_order_count_turn')
            hand_history.hero_relative_position_category_turn = street_metrics.get('hero_relative_position_category_turn')
            hand_history.hero_position_vs_preflop_raiser_turn = street_metrics.get('hero_position_vs_preflop_raiser_turn')
            hand_history.hero_action_order_index_river = street_metrics.get('hero_action_order_index_river')
            hand_history.hero_action_order_count_river = street_metrics.get('hero_action_order_count_river')
            hand_history.hero_relative_position_category_river = street_metrics.get('hero_relative_position_category_river')
            hand_history.hero_position_vs_preflop_raiser_river = street_metrics.get('hero_position_vs_preflop_raiser_river')
            
            # Calculate Hero results
            hero_result = next((r for r in hand_history.player_results if r.player_name == 'Hero'), None)
            if hero_result:
                hand_history.hero_net_result_chips = hero_result.net_result
                hand_history.hero_net_result_bb = hero_result.net_result / hand_history.stakes_bb if hand_history.stakes_bb > 0 else 0.0
                hand_history.hero_went_to_showdown = hero_result.showed_down
                hand_history.hero_won_at_showdown = hero_result.won_pot and hero_result.showed_down
                hand_history.hero_won_without_showdown = hero_result.won_pot and not hero_result.showed_down
            else:
                # Debug: Hero result not found - this is a critical issue
                print(f"WARNING: Hero result not found in player_results for hand {hand_history.hand_id}")
                print(f"Available players: {[r.player_name for r in hand_history.player_results]}")
                # Set to 0 as fallback
                hand_history.hero_net_result_chips = 0.0
                hand_history.hero_net_result_bb = 0.0
            
            return hand_history
        except Exception as e:
            print(f"Error parsing hand to history: {e}")
            import traceback
            traceback.print_exc()
            return None  # Return None instead of crashing so reprocessing can continue
    
    def _reconstruct_action_summary(self, hand_history: HandHistory) -> str:
        """Reconstruct action summary string from HandHistory actions for legacy compatibility"""
        preflop_actions = [a for a in hand_history.actions if a.street == 'preflop']
        action_lines = []
        
        for action in preflop_actions:
            if action.action_type in ['post_sb', 'post_bb']:
                continue  # Skip blind postings in action summary
            
            action_str = f"{action.actor} "
            if action.action_type == 'fold':
                action_str += "folds"
            elif action.action_type == 'check':
                action_str += "checks"
            elif action.action_type == 'call':
                action_str += f"calls ({action.amount:.2f})"
            elif action.action_type == 'bet':
                action_str += f"bets ({action.amount:.2f})"
            elif action.action_type in ['raise', 'all_in']:
                if action.bet_size_total:
                    raise_amount = action.bet_size_total - (action.to_call_before or 0)
                    action_str += f"raises {raise_amount:.2f} to {action.bet_size_total:.2f}"
                    if action.is_all_in:
                        action_str += " (all in)"
                else:
                    action_str += f"raises {action.amount:.2f}"
                    if action.is_all_in:
                        action_str += " (all in)"
            
            action_lines.append(action_str)
        
        return "\n".join(action_lines)
    
    def _reconstruct_postflop_action_summary(self, hand_history: HandHistory) -> str:
        """Reconstruct postflop action summary string for legacy compatibility"""
        postflop_actions = [a for a in hand_history.actions if a.street in ['flop', 'turn', 'river']]
        action_lines = []

        def format_action_line(action):
            action_str = f"{action.actor} "
            if action.action_type == 'fold':
                action_str += "folds"
            elif action.action_type == 'check':
                action_str += "checks"
            elif action.action_type == 'call':
                action_str += f"calls ({action.amount:.2f})"
            elif action.action_type == 'bet':
                action_str += f"bets ({action.amount:.2f})"
            elif action.action_type in ['raise', 'all_in']:
                if action.bet_size_total:
                    raise_amount = action.bet_size_total - (action.to_call_before or 0)
                    action_str += f"raises {raise_amount:.2f} to {action.bet_size_total:.2f}"
                    if action.is_all_in:
                        action_str += " (all in)"
                else:
                    action_str += f"raises {action.amount:.2f}"
                    if action.is_all_in:
                        action_str += " (all in)"
            return action_str

        if hand_history.board_flop:
            flop_cards = " ".join(hand_history.board_flop)
            action_lines.append(f"** Dealing Flop **: [{flop_cards}]")
            for action in [a for a in postflop_actions if a.street == 'flop']:
                action_lines.append(format_action_line(action))

        if hand_history.turn_card:
            action_lines.append(f"** Dealing Turn **: [{hand_history.turn_card}]")
            for action in [a for a in postflop_actions if a.street == 'turn']:
                action_lines.append(format_action_line(action))

        if hand_history.river_card:
            action_lines.append(f"** Dealing River **: [{hand_history.river_card}]")
            for action in [a for a in postflop_actions if a.street == 'river']:
                action_lines.append(format_action_line(action))

        return "\n".join(action_lines)
    
    def hand_history_to_dataframe_row(self, hand_history: HandHistory) -> Dict[str, Any]:
        """Convert HandHistory object to dictionary for DataFrame"""
        # Reconstruct legacy action summary strings
        action_summary = self._reconstruct_action_summary(hand_history)
        postflop_action_summary = self._reconstruct_postflop_action_summary(hand_history)
        
        # Reconstruct hand string format
        hero_cards = []
        if hand_history.hero_hole_card_1 and hand_history.hero_hole_card_2:
            hero_cards = [hand_history.hero_hole_card_1, hand_history.hero_hole_card_2]
        hand_str = f"[{', '.join(hero_cards)}]" if hero_cards else "[]"
        
        # Reconstruct summary string (match original format for compatibility)
        hero_result = hand_history.hero_net_result_chips
        hero_ending_stack = 0.0
        if hand_history.player_results:
            hero_result_obj = next((r for r in hand_history.player_results if r.player_name == 'Hero'), None)
            if hero_result_obj:
                hero_ending_stack = hero_result_obj.ending_stack
        
        # Create summary in format that matches original hand histories
        # Use simple format that process_summary can parse
        if hero_result > 0:
            summary_str = f"Hero balance ${hero_ending_stack:.2f}, net +${hero_result:.2f}"
        elif hero_result < 0:
            summary_str = f"Hero balance ${hero_ending_stack:.2f}, lost ${abs(hero_result):.2f}"
        else:
            summary_str = f"Hero balance ${hero_ending_stack:.2f}, didn't bet (folded)"
        
        row = {
            # Basic metadata
            'hand_id': hand_history.hand_id,
            'table_name': hand_history.table_name,
            'stakes_sb': hand_history.stakes_sb,
            'stakes_bb': hand_history.stakes_bb,
            'bb_stake': hand_history.stakes_bb,  # For backward compatibility
            'currency': hand_history.currency,
            'game_type': hand_history.game_type,
            'limit_type': hand_history.limit_type,
            'max_players': hand_history.max_players,
            'players_dealt_in': hand_history.players_dealt_in,
            'button_seat': hand_history.button_seat,
            'timestamp': hand_history.timestamp,
            
            # Position
            'position': hand_history.hero_preflop_absolute_position,
            'no_players': hand_history.players_dealt_in,
            
            # Hole cards (legacy format)
            'hero_hole_card_1': hand_history.hero_hole_card_1,
            'hero_hole_card_2': hand_history.hero_hole_card_2,
            'hand': hero_cards,
            'Hand': hand_str,  # Legacy format: "[card1, card2]"
            
            # Board cards
            'flop_card_1': hand_history.flop_card_1,
            'flop_card_2': hand_history.flop_card_2,
            'flop_card_3': hand_history.flop_card_3,
            'turn_card': hand_history.turn_card,
            'river_card': hand_history.river_card,
            'flop_cards': hand_history.board_flop,
            'turn_cards': hand_history.board_turn,
            'river_cards': hand_history.board_river,
            'board_all': hand_history.board_all,
            
            # Flop/Turn/River reached
            'flop': len(hand_history.board_flop) > 0,
            'Flop': len(hand_history.board_flop) > 0,  # Legacy
            'turn': hand_history.turn_card is not None,
            'river': hand_history.river_card is not None,
            
            # Results
            'hand_result': hand_history.hero_net_result_chips,
            'hero_net_result_bb': hand_history.hero_net_result_bb,
            'final_pot': hand_history.final_pot,
            'rake': hand_history.rake,
            
            # Legacy action summary strings (for csv_process_poker_hand)
            'Action Summary': action_summary,
            'Post Flop Action': postflop_action_summary,
            'Summary': summary_str,
            
            # Preflop analytics
            'opened_pot': hand_history.opened_pot,
            'limped': hand_history.limped,
            'had_3bet_opportunity': hand_history.had_3bet_opportunity,
            'did_3bet': hand_history.did_3bet,
            'had_4bet_opportunity': hand_history.had_4bet_opportunity,
            'did_4bet': hand_history.did_4bet,
            'faced_open_raise': hand_history.faced_open_raise,
            'faced_3bet': hand_history.faced_3bet,
            'faced_4bet': hand_history.faced_4bet,
            'preflop_role': hand_history.preflop_role,
            'preflop_aggressor': hand_history.preflop_aggressor,
            
            # Postflop metrics
            'players_see_flop': hand_history.players_see_flop,
            'players_see_turn': hand_history.players_see_turn,
            'players_see_river': hand_history.players_see_river,
            'hero_saw_flop': hand_history.hero_saw_flop,
            'hero_saw_turn': hand_history.hero_saw_turn,
            'hero_saw_river': hand_history.hero_saw_river,
            'players_active_on_flop': hand_history.players_active_on_flop,
            'players_active_on_turn': hand_history.players_active_on_turn,
            'players_active_on_river': hand_history.players_active_on_river,
            'hero_is_active_on_flop': hand_history.hero_is_active_on_flop,
            'hero_is_active_on_turn': hand_history.hero_is_active_on_turn,
            'hero_is_active_on_river': hand_history.hero_is_active_on_river,
            'hero_action_order_index_flop': hand_history.hero_action_order_index_flop,
            'hero_action_order_count_flop': hand_history.hero_action_order_count_flop,
            'hero_relative_position_category_flop': hand_history.hero_relative_position_category_flop,
            'hero_position_vs_preflop_raiser_flop': hand_history.hero_position_vs_preflop_raiser_flop,
            'hero_action_order_index_turn': hand_history.hero_action_order_index_turn,
            'hero_action_order_count_turn': hand_history.hero_action_order_count_turn,
            'hero_relative_position_category_turn': hand_history.hero_relative_position_category_turn,
            'hero_position_vs_preflop_raiser_turn': hand_history.hero_position_vs_preflop_raiser_turn,
            'hero_action_order_index_river': hand_history.hero_action_order_index_river,
            'hero_action_order_count_river': hand_history.hero_action_order_count_river,
            'hero_relative_position_category_river': hand_history.hero_relative_position_category_river,
            'hero_position_vs_preflop_raiser_river': hand_history.hero_position_vs_preflop_raiser_river,
            
            # Store actions and raw hand
            'actions': hand_history.actions,
            'Raw Hand': hand_history.raw_hand
        }
        
        # Calculate VPIP from HandHistory fields (more reliable than parsing Action Summary)
        vpip = False
        original_position = hand_history.hero_preflop_absolute_position
        position = original_position  # Start with original position
        result = hand_history.hero_net_result_chips
        bb_stake = hand_history.stakes_bb
        sb_stake = hand_history.stakes_sb

        # CRITICAL: Calculate VPIP using ORIGINAL position to avoid incorrect reclassification
        # Position correction can incorrectly change UTG to SB/BB, making UTG VPIP 0%
        # We'll correct position AFTER VPIP calculation for display purposes, but use original for VPIP logic
        
        # Check if Hero posted SB or BB from actions (for position correction later)
        hero_posted_sb = False
        hero_posted_bb = False
        for action in hand_history.actions:
            if action.actor == 'Hero' and action.street == 'preflop':
                if action.action_type == 'post_sb':
                    hero_posted_sb = True
                elif action.action_type == 'post_bb':
                    hero_posted_bb = True
        
        # Also check raw hand for blind posting (in case actions weren't parsed)
        if not hero_posted_sb and not hero_posted_bb and hand_history.raw_hand:
            if 'Hero posts small blind' in hand_history.raw_hand:
                hero_posted_sb = True
            elif 'Hero posts big blind' in hand_history.raw_hand:
                hero_posted_bb = True
        
        # CRITICAL FIX: Use ORIGINAL position for VPIP calculation to prevent incorrect reclassification
        # Only correct position for obvious cases (Hero posted blind but position is wrong)
        # But use original position for VPIP logic to ensure accuracy
        vpip_position = original_position  # Use original position for VPIP calculation
        
        # Safety check: If position is None, skip VPIP calculation (shouldn't happen but safeguard)
        if vpip_position is None:
            vpip_position = position  # Fallback to corrected position if original is None
        
        # First check: Did Hero take voluntary preflop action? (Most reliable)
        # Position-specific logic: UTG can only limp or raise, not 3-bet/4-bet
        # Use ORIGINAL position for VPIP calculation to prevent incorrect reclassification
        if vpip_position == 'UTG':
            # UTG is first to act - can only limp or raise (RFI)
            if hand_history.opened_pot or hand_history.limped:
                vpip = True
            # Also check actions directly as a fallback (in case opened_pot/limped flags are wrong)
            if not vpip:
                preflop_actions = [a for a in hand_history.actions if a.street == 'preflop']
                hero_actions = [a for a in preflop_actions if a.actor == 'Hero']
                
                # Check if Hero raised (opened pot)
                for action in hero_actions:
                    if action.action_type in ['bet', 'raise', 'all_in']:
                        # Check if this was the first raise (opened pot)
                        # Count raises before this action (excluding blind postings)
                        raises_before = sum(1 for a in preflop_actions 
                                          if a.action_index < action.action_index 
                                          and a.action_type in ['bet', 'raise', 'all_in']
                                          and a.action_type not in ['post_sb', 'post_bb'])
                        if raises_before == 0:
                            vpip = True
                            break
                
                # Check if Hero limped (called BB without raising)
                if not vpip:
                    for action in hero_actions:
                        if action.action_type == 'call':
                            # Check if this call was to the BB (limp)
                            # For UTG, calling BB means limping
                            if action.to_call_before == hand_history.stakes_bb or action.to_call_before == 0:
                                # Make sure there were no raises before this call
                                raises_before_call = sum(1 for a in preflop_actions 
                                                        if a.action_index < action.action_index 
                                                        and a.action_type in ['bet', 'raise', 'all_in']
                                                        and a.action_type not in ['post_sb', 'post_bb'])
                                if raises_before_call == 0:
                                    vpip = True
                                    break
        elif vpip_position in ['HJ', 'MP', 'CO', 'BTN']:
            # These positions can limp, raise, 3-bet, or 4-bet
            if hand_history.opened_pot or hand_history.limped or hand_history.did_3bet or hand_history.did_4bet:
                vpip = True
        elif vpip_position == 'SB':
            # SB can limp, raise, 3-bet, or 4-bet (but not call BB - that's posting blind)
            if hand_history.opened_pot or hand_history.limped or hand_history.did_3bet or hand_history.did_4bet:
                vpip = True
        elif vpip_position == 'BB':
            # BB can check, call, raise, 3-bet, or 4-bet
            # But just checking/folding is NOT VPIP
            if hand_history.opened_pot or hand_history.limped or hand_history.did_3bet or hand_history.did_4bet:
                vpip = True
            # BB calling a raise would be handled in fallback logic via action_data
            # Check if BB faced a raise and called (cold call)
            if not vpip and hand_history.faced_open_raise:
                # Check if Hero called the raise
                preflop_actions = [a for a in hand_history.actions if a.street == 'preflop']
                hero_called_raise = False
                for action in preflop_actions:
                    if action.actor == 'Hero' and action.action_type == 'call' and action.to_call_before > hand_history.stakes_bb:
                        hero_called_raise = True
                        break
                if hero_called_raise:
                    vpip = True
        
        # Second check: Did Hero see the flop? (requires VPIP - they put chips in preflop)
        # This is a reliable indicator - if Hero saw the flop, they must have put chips in preflop
        if not vpip and hand_history.hero_saw_flop:
            vpip = True
        
        # For UTG specifically: If Hero saw the flop, they MUST have raised or limped (VPIP)
        # This is a critical check because UTG can't see the flop without putting chips in
        if vpip_position == 'UTG' and not vpip and hand_history.hero_saw_flop:
            vpip = True
        
        # Third check: Non-zero result (but exclude blind-only losses and UTG folds)
        if not vpip and result != 0:
            if vpip_position == 'UTG':
                # UTG: Only mark as VPIP if result is significantly non-zero
                # Small negative values (-0.1, -0.25) might be parsing errors for folds
                # Only trust non-zero result if it's substantial (more than just a small rounding error)
                if abs(result) > 0.01:  # More than 1 cent difference
                    # But still need to verify Hero actually took action
                    # If opened_pot or limped is False, result might be a parsing error
                    if hand_history.opened_pot or hand_history.limped or hand_history.hero_saw_flop:
                        vpip = True
                    # If no action detected but result is large, trust the result
                    elif abs(result) > bb_stake * 0.5:  # Result is substantial (more than half BB)
                        vpip = True
                # Small results (< 1 cent) are likely parsing errors - don't mark as VPIP
            elif vpip_position == 'BB':
                # BB: Check if result is just from posting BB and folding
                if abs(result + bb_stake) <= bb_stake * 0.05:
                    # Result is very close to -BB, likely just posted and folded
                    vpip = False
                else:
                    # Result is significantly different from -BB
                    # But only mark as VPIP if Hero actually took action or saw flop
                    # (to avoid counting blind-only losses with small rounding differences)
                    if hand_history.opened_pot or hand_history.limped or hand_history.did_3bet or hand_history.did_4bet or hand_history.hero_saw_flop:
                        vpip = True
                    # If no action detected but result is substantial, trust the result
                    elif abs(result) > bb_stake * 0.5:  # Result is substantial (more than half BB)
                        vpip = True
                    # Otherwise, likely a blind-only loss with small rounding difference
                    else:
                        vpip = False
            elif vpip_position == 'SB':
                # SB: Check if result is just from posting SB and folding
                if abs(result + sb_stake) <= sb_stake * 0.05:
                    # Result is very close to -SB, likely just posted and folded
                    vpip = False
                else:
                    # Result is significantly different from -SB
                    # But only mark as VPIP if Hero actually took action or saw flop
                    # (to avoid counting blind-only losses with small rounding differences)
                    if hand_history.opened_pot or hand_history.limped or hand_history.did_3bet or hand_history.did_4bet or hand_history.hero_saw_flop:
                        vpip = True
                    # If no action detected but result is substantial, trust the result
                    elif abs(result) > bb_stake * 0.5:  # Result is substantial (more than half BB)
                        vpip = True
                    # Otherwise, likely a blind-only loss with small rounding difference
                    else:
                        vpip = False
            else:
                # Other positions (HJ, MP, CO, BTN): Any non-zero result means VPIP
                # (They can't have non-zero result without putting chips in)
                vpip = True
        # Note: If Hero folded preflop without action (except blinds), vpip remains False
        
        # Now correct position for display/storage (but VPIP was calculated using original position)
        # Only correct position for obvious cases where Hero posted blind but position is wrong
        # CRITICAL: Be very conservative - only correct if Hero definitely posted the blind
        # Don't correct UTG positions unless we're 100% certain Hero posted a blind
        if hero_posted_sb and position != 'SB':
            # Only correct if we're sure Hero posted SB (not just a guess)
            position = 'SB'
        elif hero_posted_bb and position != 'BB':
            # Only correct if we're sure Hero posted BB (not just a guess)
            position = 'BB'
        # Additional safety: If position is UTG but result matches blind posting EXACTLY, position might be wrong
        # BUT: Be EXTREMELY conservative - only correct if result matches blind EXACTLY and Hero definitely posted it
        # This should rarely trigger for legitimate UTG hands
        if position == 'UTG' and result != 0 and result < 0:
            # Only correct if result matches blind EXACTLY (within 0.1% tolerance) AND Hero definitely posted it
            if (abs(result + sb_stake) <= sb_stake * 0.001 and hero_posted_sb and not hand_history.hero_saw_flop):
                # Result is exactly -SB, Hero posted SB, didn't see flop - must be SB
                position = 'SB'
            elif (abs(result + bb_stake) <= bb_stake * 0.001 and hero_posted_bb and not hand_history.hero_saw_flop):
                # Result is exactly -BB, Hero posted BB, didn't see flop - must be BB
                position = 'BB'
            # Otherwise, trust the position calculation - don't change UTG
        
        # Update row with corrected position (for display) but VPIP was calculated using original position
        row['position'] = position
        # Store original position for debugging/verification
        row['hero_preflop_absolute_position'] = original_position
        
        row['vpip'] = vpip
        
        return row

    def process_hands(self, hand_list):
        """Process hands using new robust parser"""
        processed_hands = []
        failed_hands = 0
        for hand in hand_list:
            if "Hero" not in hand:
                continue
            
            try:
                # Parse hand into HandHistory object
                hand_history = self.parse_hand_to_history(hand)
                if not hand_history:
                    failed_hands += 1
                    continue
                
                # Convert to dictionary format for backward compatibility
                hand_dict = self.hand_history_to_dataframe_row(hand_history)
                
                # Add legacy fields that csv_process_poker_hand expects
                hand_dict["Hero Position"] = hand_dict.get('position', '')
                hand_dict["Number Players"] = hand_dict.get('no_players', 6)
                hand_dict["SB Stake"] = hand_dict.get('stakes_sb', 0.0)
                hand_dict["BB Stake"] = hand_dict.get('stakes_bb', 0.0)
                
                # Legacy HU fields (will be recalculated by flop_HU_with_hero in csv_process_poker_hand)
                # For now, calculate from active players
                hand_dict["HU_hero_flop"] = hand_dict.get('hero_is_active_on_flop', False) and len(hand_dict.get('players_active_on_flop', [])) == 2
                hand_dict["HU_hero_turn"] = hand_dict.get('hero_is_active_on_turn', False) and len(hand_dict.get('players_active_on_turn', [])) == 2
                hand_dict["HU_hero_river"] = hand_dict.get('hero_is_active_on_river', False) and len(hand_dict.get('players_active_on_river', [])) == 2
                
                processed_hands.append(hand_dict)
            except Exception as e:
                failed_hands += 1
                print(f"Error processing individual hand: {str(e)}")
                continue
        
        if failed_hands > 0:
            print(f"Warning: {failed_hands} hands failed to process")
        
        if len(processed_hands) == 0:
            print("Error: No hands were successfully processed")
            return pd.DataFrame()
        
        try:
            result_df = self.csv_process_poker_hand(processed_hands)
            if result_df is None or result_df.empty:
                print("Error: csv_process_poker_hand returned empty DataFrame")
                return pd.DataFrame()
            return result_df
        except Exception as e:
            import traceback
            print(f"Error in csv_process_poker_hand: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return pd.DataFrame()

    def is_ladbrooks_hands(self):
        try:
            hands = self.data.strip().split("***** Hand History For Game")
            if len(hands) <= 1:
                return False, "Basic processing impossible: No hand histories found.", self.data
            valid_hands = [hand.strip() for hand in hands[1:] if self.validate_hand(hand.strip())]
            if len(valid_hands) < len(hands) - 1:
                return True, "Dataset has trimmed non six-max hands", valid_hands
            return True, "Dataset is valid", valid_hands
        except Exception as e:
            return False, f"Validation Error: {e}", []

    def validate_hand(self, hand):
        try:
            if "** Dealing down cards **" not in hand or "** Summary **" not in hand:
                return False

            lines = [ln.strip() for ln in hand.split("\n") if ln.strip()]
            game_description_pattern = r"^\d+\.\d+/\d+\.\d+ Texas Holdem Game Table \(NL\) - .+$"
            total_players_pattern = r"^Total number of players : \d+/6$"

            has_game_line = any(re.match(game_description_pattern, ln) for ln in lines)
            has_total_players = any(re.match(total_players_pattern, ln) for ln in lines)

            return has_game_line and has_total_players
        except Exception:
            return False

    def calculate_vpip(self, df):
        if df is None or df.empty or 'vpip' not in df.columns:
            return {
                "num_viable_hands": 0,
                "vpip_count": 0,
                "general_vpip": 0.0,
                "positional_vpip": {}
            }
        
        total_hands = len(df)
        
        # Convert vpip to numeric (True/False -> 1/0) to ensure sum works correctly
        # Handle both boolean and string representations
        vpip_series = df['vpip'].apply(lambda x: 1 if (x is True or x == True or str(x).lower() == 'true' or x == 1) else 0)
        vpip_true_count = int(vpip_series.sum())
        
        general_vpip_percent = round((vpip_true_count / total_hands) * 100, 2) if total_hands > 0 else 0

        # Calculate positional VPIP
        position_vpip_counts = df.groupby('position').apply(lambda g: g['vpip'].apply(lambda x: 1 if (x is True or x == True or str(x).lower() == 'true' or x == 1) else 0).sum())
        position_hand_counts = df['position'].value_counts()
        position_vpip_percent = (position_vpip_counts / position_hand_counts * 100).fillna(0)

        # For 6-handed: UTG, MP, CO, BTN, SB, BB (HJ is only for 5-handed)
        ordered_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        # Reindex will fill missing positions with NaN, then fillna(0) converts to 0
        # This gracefully handles any unexpected positions (like HJ from old data)
        position_vpip_percent = position_vpip_percent.reindex(ordered_positions).fillna(0)
        position_hand_counts_ordered = position_hand_counts.reindex(ordered_positions).fillna(0)

        rounded_positional_vpip = {pos: round(float(vpip), 2) for pos, vpip in position_vpip_percent.to_dict().items()}
        rounded_positional_hand_counts = {pos: int(hand_count) for pos, hand_count in position_hand_counts_ordered.to_dict().items()}

        return {
            "num_viable_hands": total_hands,
            "vpip_count": vpip_true_count,  # Actual number of VPIP hands
            "general_vpip": general_vpip_percent,
            "positional_vpip": rounded_positional_vpip,
            "positional_hand_counts": rounded_positional_hand_counts  # Number of hands per position
        }

    def calculate_rfi_vpip_metrics(self, df):
        """
        Calculate RFI VPIP metrics.
        RFI VPIP = Hands where Hero was the FIRST person to open raise into the pot (RFI only, not limp).
        Only counts non-BB positions (BB can't RFI since they're already in the pot).
        """
        rfi_count = 0  # Total RFI hands
        # Include all possible positions including HJ (Hijack)
        position_rfi_counts = {'UTG': 0, 'HJ': 0, 'MP': 0, 'CO': 0, 'BTN': 0, 'SB': 0}
        position_total_counts = {'UTG': 0, 'HJ': 0, 'MP': 0, 'CO': 0, 'BTN': 0, 'SB': 0}

        for _, row in df.iterrows():
            position = row.get('position', None)
            if position and position != 'BB':
                # Initialize position if not already in dict (defensive programming)
                if position not in position_total_counts:
                    position_total_counts[position] = 0
                    position_rfi_counts[position] = 0
                position_total_counts[position] += 1
                # RFI = Raise First In (not limp, not call)
                # Use is_dict() to properly check if rfi is a dictionary (truthy) vs 0 or '0' (falsy)
                if self.is_dict(row.get('rfi', 0)):
                    rfi_count += 1
                    position_rfi_counts[position] += 1

        # Calculate RFI VPIP percentages
        total_viable_hands = sum(position_total_counts.values())
        general_rfi_vpip_percent = round((rfi_count / total_viable_hands) * 100, 2) if total_viable_hands > 0 else 0

        position_rfi_vpip_percent = {}
        for position in position_rfi_counts:
            total_position_hands = position_total_counts[position]
            position_rfi_vpip_percent[position] = round((position_rfi_counts[position] / total_position_hands) * 100,
                                                        2) if total_position_hands > 0 else 0

        ordered_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB']
        position_rfi_vpip_percent = {pos: position_rfi_vpip_percent.get(pos, 0) for pos in ordered_positions}

        return {
            "num_viable_hands": total_viable_hands,  # Total hands in non-BB positions
            "rfi_count": rfi_count,  # Actual number of RFI hands
            "general_rfi_vpip": general_rfi_vpip_percent,
            "positional_rfi_vpip": position_rfi_vpip_percent
        }

    def is_dict(self, val):
        return val != '0' and val != 0

    def get_three_bet_metrics(self, data_frame):
        three_bet_data = {}
        position_values = {'MP': 0, 'CO': 0, 'BTN': 0, 'SB': 0, 'BB': 0}
        three_bet_data['Viable_hands'] = len(data_frame)
        filtered_df = data_frame[(data_frame['three_bet'].apply(self.is_dict))]

        three_bet_data['Num_three_bets'] = len(filtered_df)

        num_position_values = position_values.copy()
        num_three_bet_wins = 0
        num_three_bet_wins_position = position_values.copy()
        sum_results = 0
        sum_results_position = position_values.copy()
        sum_results_position_no_flop = position_values.copy()
        sum_results_position_flop = position_values.copy()

        for _, row in filtered_df.iterrows():
            three_bet_dict = row['three_bet']
            if row['position'] in num_position_values:
                num_position_values[row['position']] += 1
                sum_results_position[row['position']] += row['hand_result'] / row['bb_stake']
                if not row['flop']:
                    sum_results_position_no_flop[row['position']] += row['hand_result'] / row['bb_stake']
                    if row['hand_result'] > 0:
                        num_three_bet_wins += 1
                        num_three_bet_wins_position[row['position']] += 1
                else:
                    sum_results_position_flop[row['position']] += row['hand_result'] / row['bb_stake']
            sum_results += row['hand_result'] / row['bb_stake']

        three_bet_data['Num_three_bets_position'] = {pos: round(value, 2) for pos, value in num_position_values.items()}
        three_bet_data['Num_three_bet_wins'] = round(num_three_bet_wins, 2)
        three_bet_data['Num_three_bet_wins_position'] = {pos: round(value, 2) for pos, value in num_three_bet_wins_position.items()}
        three_bet_data['Sum_results_BB'] = round(sum_results, 2)
        three_bet_data['Avg_result_BB'] = round(sum_results / len(filtered_df), 2) if len(filtered_df) > 0 else 0
        three_bet_data['Sum_results_position_BB'] = {pos: round(value, 2) for pos, value in sum_results_position.items()}
        three_bet_data['Sum_results_position_no_flop_BB'] = {pos: round(value, 2) for pos, value in sum_results_position_no_flop.items()}
        three_bet_data['Sum_results_position_flop_BB'] = {pos: round(value, 2) for pos, value in sum_results_position_flop.items()}

        return three_bet_data

    def get_iso_raise_metrics(self, dataframe):
        """
        Calculate iso-raise metrics.
        Iso-raise = Hero raises after someone limped (to isolate limpers).
        Detection: Check if someone called (limped) before Hero raised.
        """
        iso_raise_data = {}
        position_values = {'MP': 0, 'CO': 0, 'BTN': 0, 'SB': 0, 'BB': 0}
        
        # Viable hands for iso-raise = all hands (Hero could iso-raise from any position except UTG)
        iso_raise_data['Viable_hands'] = len(dataframe)
        
        # Filter for iso-raises: Hero raised after someone limped
        iso_raise_hands = []
        
        for _, row in dataframe.iterrows():
            position = row['position']
            
            # UTG can't iso-raise (they're first to act)
            if position == 'UTG':
                continue
            
            # Check if Hero raised
            # For iso-raise, Hero must have RFI'd (not 3-bet, 4-bet, etc.)
            # because iso-raise is specifically raising after limpers (no raise before)
            hero_rfi = False
            if self.is_dict(row.get('rfi', 0)):
                hero_rfi = True
            
            # If Hero didn't RFI, skip (3-bets, 4-bets after limpers aren't iso-raises)
            if not hero_rfi:
                continue
            
            # Check if there was a limp (call) before Hero's action
            # An iso-raise is when Hero raises after someone limped (called BB)
            raw_hand = row.get('Raw Hand', '')
            is_iso_raise = False
            
            if raw_hand and isinstance(raw_hand, str):
                # Extract preflop action section
                try:
                    if "** Dealing down cards **" in raw_hand:
                        if "** Dealing Flop **" in raw_hand:
                            preflop_section = raw_hand.split("** Dealing down cards **")[1].split("** Dealing Flop **")[0]
                        elif "** Summary **" in raw_hand:
                            preflop_section = raw_hand.split("** Dealing down cards **")[1].split("** Summary **")[0]
                        else:
                            preflop_section = ""
                    else:
                        preflop_section = ""
                    
                    # Parse action sequence to detect iso-raise
                    # Iso-raise = call(s) before Hero, then Hero raises (no raise before Hero)
                    action_sequence = []
                    
                    for line in preflop_section.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Skip blind postings and dealing cards
                        if 'posts' in line.lower() and ('small blind' in line.lower() or 'big blind' in line.lower()):
                            continue
                        if 'dealing' in line.lower() or 'dealt' in line.lower():
                            continue
                        
                        # Track actions before Hero
                        if 'Hero' not in line:
                            if 'calls' in line.lower():
                                action_sequence.append('call')
                            elif 'raises' in line.lower():
                                action_sequence.append('raise')
                            elif 'folds' in line.lower():
                                action_sequence.append('fold')
                        else:
                            # Hero's action
                            if 'raises' in line.lower():
                                # Check if there were calls (limps) before Hero and no raises
                                if 'call' in action_sequence and 'raise' not in action_sequence:
                                    is_iso_raise = True
                            break  # Stop after Hero's first action
                
                except Exception:
                    pass
            
            # If we found a limp before Hero RFI'd, it's an iso-raise
            if is_iso_raise and hero_rfi and position in position_values:
                iso_raise_hands.append(row)
        
        # Create filtered dataframe
        if iso_raise_hands:
            filtered_df = pd.DataFrame(iso_raise_hands)
        else:
            filtered_df = pd.DataFrame()
        
        iso_raise_data['Num_iso_raises'] = len(filtered_df)
        
        num_position_values = position_values.copy()
        num_iso_raise_wins = 0
        num_iso_raise_wins_position = position_values.copy()
        sum_results = 0
        sum_results_position = position_values.copy()
        sum_results_position_no_flop = position_values.copy()
        sum_results_position_flop = position_values.copy()
        
        for _, row in filtered_df.iterrows():
            if row['position'] in num_position_values:
                num_position_values[row['position']] += 1
                bb_result = row['hand_result'] / row['bb_stake']
                sum_results_position[row['position']] += bb_result
                if not row['flop']:
                    sum_results_position_no_flop[row['position']] += bb_result
                    if row['hand_result'] > 0:
                        num_iso_raise_wins += 1
                        num_iso_raise_wins_position[row['position']] += 1
                else:
                    sum_results_position_flop[row['position']] += bb_result
            sum_results += row['hand_result'] / row['bb_stake']
        
        iso_raise_data['Num_iso_raises_position'] = {pos: int(value) for pos, value in num_position_values.items()}
        iso_raise_data['Num_iso_raise_wins'] = int(num_iso_raise_wins)
        iso_raise_data['Num_iso_raise_wins_position'] = {pos: int(value) for pos, value in num_iso_raise_wins_position.items()}
        iso_raise_data['Sum_results_BB'] = round(sum_results, 2)
        iso_raise_data['Avg_result_BB'] = round(sum_results / len(filtered_df), 2) if len(filtered_df) > 0 else 0
        iso_raise_data['Sum_results_position_BB'] = {pos: round(value, 2) for pos, value in sum_results_position.items()}
        iso_raise_data['Sum_results_position_no_flop_BB'] = {pos: round(value, 2) for pos, value in sum_results_position_no_flop.items()}
        iso_raise_data['Sum_results_position_flop_BB'] = {pos: round(value, 2) for pos, value in sum_results_position_flop.items()}
        
        return iso_raise_data

    def calculate_in_position_percentage(self, dataframe):
        hu_flop_df = dataframe[dataframe['flop_HU_with_hero'] == True]
        total_hands = len(hu_flop_df)
        in_position_hands = hu_flop_df['flop_Position'].sum()
        in_position_percentage = (in_position_hands / total_hands) * 100 if total_hands > 0 else 0
        return round(in_position_percentage, 2), (100-round(in_position_percentage, 2))

    def process_op_bet_rates(self, op_reaction_counts):
        total = op_reaction_counts['op_check'] + op_reaction_counts['op_donk']
        Hero_op_action = {'total': 0, 'Check': 0, 'Bets': 0}
        Villain_ip_action = {'total': 0, 'Villain_cbets': 0, 'Villain_checks': 0}
        Hero_op_vs_cbet = {'total': op_reaction_counts['ip_cbet'], 'Call_cbet': 0, 'Raise_cbet': 0, 'Fold_to_cbet': 0}
        Villain_ip_vs_checkraise = {'total': 0, 'Villain_Calls': 0, 'Villain_Raises': 0, 'Villain_Folds': 0}
        Villain_ip_vs_donk = {'total': 0, 'Villain_Calls': 0, 'Villain_Raises': 0, 'Villain_Folds': 0}

        if total > 0:
            Hero_op_action['total'] = total
            Hero_op_action['Check'] = round(100 * (op_reaction_counts['op_check'] / total), 2)
            Hero_op_action['Bets'] = round(100 * (op_reaction_counts['op_donk'] / total), 2)
        if op_reaction_counts['op_check'] > 0:
            Villain_ip_action['total'] = op_reaction_counts['op_check']
            Villain_ip_action['Villain_cbets'] = round(100 * (op_reaction_counts['ip_cbet'] / Villain_ip_action['total']), 2)
            Villain_ip_action['Villain_checks'] = round(100 * (op_reaction_counts['ip_check'] / Villain_ip_action['total']), 2)
        if op_reaction_counts['ip_cbet'] > 0:
            Hero_op_vs_cbet['Call_cbet'] = round(100 * (op_reaction_counts['cbet_call'] / op_reaction_counts['ip_cbet']), 2)
            Hero_op_vs_cbet['Raise_cbet'] = round(100 * (op_reaction_counts['cbet_raise'] / op_reaction_counts['ip_cbet']), 2)
            Hero_op_vs_cbet['Fold_to_cbet'] = round(100 * (op_reaction_counts['cbet_fold'] / op_reaction_counts['ip_cbet']), 2)

        if op_reaction_counts['cbet_raise'] > 0:
            Villain_ip_vs_checkraise['total'] = op_reaction_counts['cbet_raise']
            Villain_ip_vs_checkraise['Villain_Calls'] = round(
                100 * (op_reaction_counts['call_check_raise'] / Villain_ip_vs_checkraise['total']), 2)
            Villain_ip_vs_checkraise['Villain_Raises'] = round(
                100 * (op_reaction_counts['raise_check_raise'] / Villain_ip_vs_checkraise['total']), 2)
            Villain_ip_vs_checkraise['Villain_Folds'] = round(
                100 * (op_reaction_counts['fold_check_raise'] / Villain_ip_vs_checkraise['total']), 2)
        if op_reaction_counts['op_donk'] > 0:
            Villain_ip_vs_donk['total'] = op_reaction_counts['op_donk']
            Villain_ip_vs_donk['Villain_Calls'] = round(
                100 * (op_reaction_counts['call_donk'] / Villain_ip_vs_donk['total']), 2)
            Villain_ip_vs_donk['Villain_Raises'] = round(
                100 * (op_reaction_counts['raise_donk'] / Villain_ip_vs_donk['total']), 2)
            Villain_ip_vs_donk['Villain_Folds'] = round(
                100 * (op_reaction_counts['fold_to_donk'] / Villain_ip_vs_donk['total']), 2)

        return Hero_op_action, Villain_ip_action, Hero_op_vs_cbet, Villain_ip_vs_checkraise, Villain_ip_vs_donk

    def process_ip_reaction(self, ip_reactions):
        total = ip_reactions['op_check'] + ip_reactions['op_donk']
        Villain_op_action = {'total': total, 'Villain_checks': 0, 'Villain_bets': 0}
        Hero_ip_action = {'total': ip_reactions['op_check'], 'checks': 0, 'ip_cbets': 0}
        Villain_op_vs_cbet = {'total': ip_reactions['ip_cbet'], 'Call_cbet': 0, 'Raise_cbet': 0, 'Fold_to_cbet': 0}
        Hero_ip_vs_checkraise = {'total': ip_reactions['cbet_raise'], 'Hero_Calls': 0, 'Hero_Raises': 0, 'Hero_Folds': 0}
        Hero_ip_vs_donk = {'total': ip_reactions['op_donk'], 'Hero_Calls': 0, 'Hero_Raises': 0, 'Hero_Folds': 0}

        if total > 0:
            Villain_op_action['Villain_checks'] = round(100 * (ip_reactions['op_check'] / total), 2)
            Villain_op_action['Villain_bets'] = round(100 * (ip_reactions['op_donk'] / total), 2)
        if Hero_ip_action['total'] > 0:
            Hero_ip_action['checks'] = round(100 * (ip_reactions['ip_check'] / Hero_ip_action['total']), 2)
            Hero_ip_action['ip_cbets'] = round(100 * (ip_reactions['ip_cbet'] / Hero_ip_action['total']), 2)
        if ip_reactions['ip_cbet'] > 0:
            Villain_op_vs_cbet['Call_cbet'] = round(100 * (ip_reactions['cbet_call'] / ip_reactions['ip_cbet']), 2)
            Villain_op_vs_cbet['Raise_cbet'] = round(100 * (ip_reactions['cbet_raise'] / ip_reactions['ip_cbet']), 2)
            Villain_op_vs_cbet['Fold_to_cbet'] = round(100 * (ip_reactions['cbet_fold'] / ip_reactions['ip_cbet']), 2)
        if Hero_ip_vs_checkraise['total'] > 0:
            Hero_ip_vs_checkraise['Hero_Calls'] = round(
                100 * (ip_reactions['call_check_raise'] / Hero_ip_vs_checkraise['total']), 2)
            Hero_ip_vs_checkraise['Hero_Raises'] = round(
                100 * (ip_reactions['fold_check_raise'] / Hero_ip_vs_checkraise['total']), 2)
            Hero_ip_vs_checkraise['Hero_Folds'] = round(
                100 * (ip_reactions['raise_check_raise'] / Hero_ip_vs_checkraise['total']), 2)
        if Hero_ip_vs_donk['total'] > 0:
            Hero_ip_vs_donk['Hero_Calls'] = round(100 * (ip_reactions['call_donk'] / Hero_ip_vs_donk['total']), 2)
            Hero_ip_vs_donk['Hero_Raises'] = round(100 * (ip_reactions['raise_donk'] / Hero_ip_vs_donk['total']), 2)
            Hero_ip_vs_donk['Hero_Folds'] = round(100 * (ip_reactions['fold_to_donk'] / Hero_ip_vs_donk['total']), 2)

        return Villain_op_action, Hero_ip_action, Villain_op_vs_cbet, Hero_ip_vs_checkraise, Hero_ip_vs_donk



    def calculate_bet_rates(self, dataframe, street):
        street_column = 'flop_Position'
        street_op_column = f'{street.lower()}_OP'
        street_ip_column = f'{street.lower()}_IP'

        op_reaction_counts = {
            'op_check': 0,
            'op_donk': 0,
            'ip_check': 0,
            'ip_cbet': 0,
            'cbet_fold': 0,
            'cbet_raise': 0,
            'cbet_call': 0,
            'call_check_raise': 0,
            'fold_check_raise': 0,
            'raise_check_raise': 0,
            'call_donk': 0,
            'raise_donk': 0,
            'fold_to_donk': 0
        }

        ip_reaction_counts = {
            'op_check': 0,
            'op_donk': 0,
            'ip_check': 0,
            'ip_cbet': 0,
            'cbet_fold': 0,
            'cbet_raise': 0,
            'cbet_call': 0,
            'call_check_raise': 0,
            'fold_check_raise': 0,
            'raise_check_raise': 0,
            'call_donk': 0,
            'raise_donk': 0,
            'fold_to_donk': 0
        }

        op_total_hands = 0
        ip_total_hands = 0

        hu_street_df = dataframe[dataframe[f'{street.lower()}_HU_with_hero'] == True]

        for _, row in hu_street_df.iterrows():
            ip_actions = row[street_ip_column]
            op_actions = row[street_op_column]

            # Skip if actions are missing or empty
            if not isinstance(op_actions, (list, tuple)) or not op_actions:
                continue
            if not isinstance(ip_actions, (list, tuple)) or not ip_actions:
                continue
            
            # Validate nested list structure
            if not isinstance(op_actions[0], (list, tuple)) or not op_actions[0]:
                continue
            if not isinstance(ip_actions[0], (list, tuple)) or not ip_actions[0]:
                continue

            if not row[street_column]:  # Out of Position
                op_total_hands += 1
                op_first_action = str(op_actions[0][0]).lower() if len(op_actions[0]) > 0 else ''
                ip_first_action = str(ip_actions[0][0]).lower() if len(ip_actions[0]) > 0 else ''
                
                if op_first_action == 'checks':
                    op_reaction_counts['op_check'] += 1
                    if ip_first_action == 'bets':
                        op_reaction_counts['ip_cbet'] += 1
                        if len(op_actions) > 1 and isinstance(op_actions[1], (list, tuple)) and len(op_actions[1]) > 0:
                            op_second_action = str(op_actions[1][0]).lower()
                            if op_second_action == 'calls':
                                op_reaction_counts['cbet_call'] += 1
                            elif op_second_action == 'folds':
                                op_reaction_counts['cbet_fold'] += 1
                            elif 'raises' in op_second_action or 'all-in' in op_second_action:
                                op_reaction_counts['cbet_raise'] += 1
                                if len(ip_actions) > 1 and isinstance(ip_actions[1], (list, tuple)) and len(ip_actions[1]) > 0:
                                    ip_second_action = str(ip_actions[1][0]).lower()
                                    if ip_second_action == 'folds':
                                        op_reaction_counts['fold_check_raise'] += 1
                                    elif ip_second_action == 'calls':
                                        op_reaction_counts['call_check_raise'] += 1
                                    elif 'raises' in ip_second_action or 'all-in' in ip_second_action:
                                        op_reaction_counts['raise_check_raise'] += 1
                    elif ip_first_action == 'checks':
                        op_reaction_counts['ip_check'] += 1

                elif op_first_action == 'bets':
                    op_reaction_counts['op_donk'] += 1
                    if 'raises' in ip_first_action or 'all-in' in ip_first_action:
                        op_reaction_counts['raise_donk'] += 1
                    elif ip_first_action == 'calls':
                        op_reaction_counts['call_donk'] += 1
                    elif ip_first_action == 'folds':
                        op_reaction_counts['fold_to_donk'] += 1

            elif row[street_column]:  # In Position
                ip_total_hands += 1
                op_first_action = str(op_actions[0][0]).lower() if len(op_actions[0]) > 0 else ''
                ip_first_action = str(ip_actions[0][0]).lower() if len(ip_actions[0]) > 0 else ''
                
                if op_first_action == 'checks':
                    ip_reaction_counts['op_check'] += 1
                    if ip_first_action == 'bets':
                        ip_reaction_counts['ip_cbet'] += 1
                        if len(op_actions) > 1 and isinstance(op_actions[1], (list, tuple)) and len(op_actions[1]) > 0:
                            op_second_action = str(op_actions[1][0]).lower()
                            if op_second_action == 'calls':
                                ip_reaction_counts['cbet_call'] += 1
                            elif op_second_action == 'folds':
                                ip_reaction_counts['cbet_fold'] += 1
                            elif 'raises' in op_second_action or 'all-in' in op_second_action:
                                ip_reaction_counts['cbet_raise'] += 1
                                if len(ip_actions) > 1 and isinstance(ip_actions[1], (list, tuple)) and len(ip_actions[1]) > 0:
                                    ip_second_action = str(ip_actions[1][0]).lower()
                                    if ip_second_action == 'folds':
                                        ip_reaction_counts['fold_check_raise'] += 1
                                    elif ip_second_action == 'calls':
                                        ip_reaction_counts['call_check_raise'] += 1
                                    elif 'raises' in ip_second_action or 'all-in' in ip_second_action:
                                        ip_reaction_counts['raise_check_raise'] += 1
                    elif ip_first_action == 'checks':
                        ip_reaction_counts['ip_check'] += 1

                elif op_first_action == 'bets':
                    ip_reaction_counts['op_donk'] += 1
                    if 'raises' in ip_first_action or 'all-in' in ip_first_action:
                        ip_reaction_counts['raise_donk'] += 1
                    elif ip_first_action == 'calls':
                        ip_reaction_counts['call_donk'] += 1
                    elif ip_first_action == 'folds':
                        ip_reaction_counts['fold_to_donk'] += 1

        Hero_op_action, Villain_ip_action, Hero_op_vs_cbet, Villain_ip_vs_checkraise, Villain_ip_vs_donk = self.process_op_bet_rates(
             op_reaction_counts)
        Villain_op_action, Hero_ip_action, Villain_op_vs_cbet, Hero_ip_vs_checkraise, Hero_ip_vs_donk = self.process_ip_reaction(
            ip_reaction_counts)

        return {
            f'{street}_Hero_op_action': Hero_op_action,
            f'{street}_Villain_ip_action': Villain_ip_action,
            f'{street}_Hero_op_vs_cbet': Hero_op_vs_cbet,
            f'{street}_Villain_ip_vs_checkraise': Villain_ip_vs_checkraise,
            f'{street}_Villain_ip_vs_donk': Villain_ip_vs_donk,
            f'{street}_Villain_op_action': Villain_op_action,
            f'{street}_Hero_ip_action': Hero_ip_action,
            f'{street}_Villain_op_vs_cbet': Villain_op_vs_cbet,
            f'{street}_Hero_ip_vs_checkraise': Hero_ip_vs_checkraise,
            f'{street}_Hero_ip_vs_donk': Hero_ip_vs_donk
        }

    def _extract_hero_actions_from_raw_hand(self, raw_hand, street):
        """Extract Hero's actions from raw hand history for a given street (for multiway pots)"""
        hero_actions = []
        
        try:
            # Find the street section
            street_markers = {
                'flop': '** Dealing Flop **',
                'turn': '** Dealing Turn **',
                'river': '** Dealing River **'
            }
            
            next_street_markers = {
                'flop': '** Dealing Turn **',
                'turn': '** Dealing River **',
                'river': '** Summary **'
            }
            
            street_marker = street_markers.get(street)
            next_marker = next_street_markers.get(street)
            
            if not street_marker or street_marker not in raw_hand:
                return hero_actions
            
            # Extract the section between this street and the next
            start_idx = raw_hand.find(street_marker)
            if start_idx == -1:
                return hero_actions
            
            # Find the end of this street's action
            end_idx = raw_hand.find(next_marker, start_idx)
            if end_idx == -1:
                end_idx = raw_hand.find('** Summary **', start_idx)
            
            if end_idx == -1:
                return hero_actions
            
            street_section = raw_hand[start_idx:end_idx]
            
            # Parse lines looking for Hero's actions
            # Be more flexible - look for "Hero" anywhere in the line, not just at the start
            for line in street_section.split('\n'):
                line = line.strip()
                # Skip empty lines, headers, and board card lines (which contain ':')
                if not line or line.startswith('**'):
                    continue
                
                # Skip board card lines (they have format like "** Dealing Flop ** :  [ Qd, 4d, 8c ]")
                if ':' in line and ('[' in line or 'Dealing' in line):
                    continue
                
                # Skip lines that contain "Dealing" (these are the header lines)
                if 'Dealing' in line:
                    continue
                
                # Check if this line contains Hero's action
                # Look for "Hero" anywhere in the line (with word boundaries to avoid false matches)
                # Format examples from sample:
                # "Hero checks"
                # "Hero bets (0.75)"
                # "Hero calls (2.18)"
                # "Hero folds"
                # "Hero raises 20.26 to 20.26"
                # "Hero is all-In"
                # Also handle: "Player1 checks", "Hero checks" (Hero might not be first word)
                
                # Use word boundary to match "Hero" as a whole word (not part of another word)
                # Try multiple patterns to catch different formats
                hero_match = None
                
                # Pattern 1: "Hero " at start of line (most common)
                if line.startswith('Hero '):
                    hero_match = re.search(r'Hero\s+(\w+)', line, re.IGNORECASE)
                # Pattern 2: "Hero " anywhere in line (for cases where there's whitespace before)
                elif re.search(r'\bHero\s+', line, re.IGNORECASE):
                    hero_match = re.search(r'\bHero\s+(\w+)', line, re.IGNORECASE)
                
                if hero_match:
                    potential_action = hero_match.group(1).lower()
                    
                    # Check if it's a valid action word
                    valid_actions = ['bet', 'bets', 'check', 'checks', 'call', 'calls', 'fold', 'folds', 'raise', 'raises', 'is']
                    if potential_action in valid_actions:
                        # Handle "Hero is all-In" case
                        if potential_action == 'is' and 'all-in' in line.lower():
                            # This is a bet or raise (all-in)
                            # Check if there's a "raises" earlier in the line
                            if 'raise' in line.lower():
                                action_type = 'raise'
                            else:
                                action_type = 'bet'
                            amount = 0.0  # All-in amount would be in previous action or summary
                            hero_actions.append([action_type, amount])
                        elif potential_action in ['bet', 'bets', 'check', 'checks', 'call', 'calls', 'fold', 'folds', 'raise', 'raises']:
                            action_type = potential_action.rstrip('s')  # Remove plural 's' if present
                            amount = 0.0
                            
                            # Try to extract amount from various formats
                            # Format 1: "Hero bets (2.50)" or "Hero calls (1.00)"
                            amount_match = re.search(r'\(([\d.]+)\)', line)
                            if amount_match:
                                try:
                                    amount = float(amount_match.group(1))
                                except:
                                    amount = 0.0
                            else:
                                # Format 2: "Hero raises 1.00 to 2.00"
                                raise_to_match = re.search(r'raises?\s+([\d.]+)\s+to\s+([\d.]+)', line, re.IGNORECASE)
                                if raise_to_match:
                                    try:
                                        # Use the "to" amount (final bet size)
                                        amount = float(raise_to_match.group(2))
                                    except:
                                        amount = 0.0
                            
                            hero_actions.append([action_type, amount])
        
        except Exception as e:
            # If parsing fails, return empty list
            pass
        
        return hero_actions

    def _determine_position_from_raw_hand(self, raw_hand, street):
        """Determine if Hero is IP or OOP from raw hand history by checking who acts FIRST on the street.
        This is based STRICTLY on action order AFTER the board cards are dealt, not preflop position.
        Returns True if Hero is IP (acts after at least one opponent), False if OOP (acts first), None if can't determine."""
        try:
            street_markers = {
                'flop': '** Dealing Flop **',
                'turn': '** Dealing Turn **',
                'river': '** Dealing River **'
            }
            
            next_street_markers = {
                'flop': '** Dealing Turn **',
                'turn': '** Dealing River **',
                'river': '** Summary **'
            }
            
            street_marker = street_markers.get(street)
            next_marker = next_street_markers.get(street)
            
            if not street_marker or street_marker not in raw_hand:
                return None
            
            start_idx = raw_hand.find(street_marker)
            if start_idx == -1:
                return None
            
            end_idx = raw_hand.find(next_marker, start_idx)
            if end_idx == -1:
                end_idx = raw_hand.find('** Summary **', start_idx)
            
            if end_idx == -1:
                return None
            
            street_section = raw_hand[start_idx:end_idx]
            
            # Find the first ACTION line (skip board card lines which contain ':')
            # Look for the first line that contains a player action (bet, check, call, fold, raise)
            for line in street_section.split('\n'):
                line = line.strip()
                # Skip empty lines, headers, and board card lines (which contain ':')
                if not line or line.startswith('**') or ':' in line:
                    continue
                
                # This should be an action line - check who acts first
                # Format: "PlayerName action" or "Hero action"
                if line.startswith('Hero '):
                    # Hero acts first on this street = OOP
                    return False
                elif line and not line.startswith('**'):
                    # Someone else acts before Hero = Hero is IP (acts after at least one opponent)
                    return True
            
            return None
        except:
            return None

    def calculate_hand_matrix_analysis(self, dataframe):
        """Calculate hand matrix analysis - grouped by Pairs, Suited, Offsuit"""
        analysis = {
            'Pairs': {},
            'Suited': {},
            'Offsuit': {}
        }
        rank_names = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: 'T', 9: '9', 8: '8', 7: '7', 6: '6', 5: '5', 4: '4', 3: '3', 2: '2'}
        
        for _, row in dataframe.iterrows():
            hand = row.get('hand', [])
            if not hand or not isinstance(hand, list) or len(hand) < 2:
                continue
            
            card1 = hand[0].strip().upper() if isinstance(hand[0], str) else str(hand[0]).strip().upper()
            card2 = hand[1].strip().upper() if isinstance(hand[1], str) else str(hand[1]).strip().upper()
            
            if len(card1) < 2 or len(card2) < 2:
                continue
            
            rank1 = self._parse_card_rank(card1)
            rank2 = self._parse_card_rank(card2)
            suit1 = card1[-1] if len(card1) > 1 else ''
            suit2 = card2[-1] if len(card2) > 1 else ''
            
            # Determine hand type and combo name
            if rank1 == rank2:
                hand_type = 'Pairs'
                # For pairs, use both ranks (e.g., AA, KK)
                combo = f'{rank_names.get(rank1, str(rank1))}{rank_names.get(rank2, str(rank2))}'
            elif suit1 == suit2:
                hand_type = 'Suited'
                # Order ranks (higher first) for suited
                if rank1 > rank2:
                    combo = f'{rank_names.get(rank1, str(rank1))}{rank_names.get(rank2, str(rank2))}s'
                else:
                    combo = f'{rank_names.get(rank2, str(rank2))}{rank_names.get(rank1, str(rank1))}s'
            else:
                hand_type = 'Offsuit'
                # Order ranks (higher first) for offsuit
                if rank1 > rank2:
                    combo = f'{rank_names.get(rank1, str(rank1))}{rank_names.get(rank2, str(rank2))}o'
                else:
                    combo = f'{rank_names.get(rank2, str(rank2))}{rank_names.get(rank1, str(rank1))}o'
            
            # Initialize combo in the appropriate hand type
            if combo not in analysis[hand_type]:
                analysis[hand_type][combo] = {
                    'total_hands': 0,
                    'total_bb_earnings': 0.0,
                    'avg_bb_per_hand': 0.0,
                    'combos': {}  # Store individual suit combos (e.g., AsKh, AsKd, etc.)
                }
            
            # Also track individual suit combos for detailed breakdown
            suit_combo = f'{card1}{card2}'
            if suit_combo not in analysis[hand_type][combo]['combos']:
                analysis[hand_type][combo]['combos'][suit_combo] = {
                    'total_hands': 0,
                    'total_bb_earnings': 0.0,
                    'avg_bb_per_hand': 0.0
                }
            
            bb_earnings = row['hand_result'] / row['bb_stake']
            analysis[hand_type][combo]['total_hands'] += 1
            analysis[hand_type][combo]['total_bb_earnings'] += bb_earnings
            analysis[hand_type][combo]['combos'][suit_combo]['total_hands'] += 1
            analysis[hand_type][combo]['combos'][suit_combo]['total_bb_earnings'] += bb_earnings
        
        # Calculate averages
        for hand_type in analysis:
            for combo in analysis[hand_type]:
                if analysis[hand_type][combo]['total_hands'] > 0:
                    analysis[hand_type][combo]['avg_bb_per_hand'] = round(
                        analysis[hand_type][combo]['total_bb_earnings'] / analysis[hand_type][combo]['total_hands'], 2
                    )
                    analysis[hand_type][combo]['total_bb_earnings'] = round(analysis[hand_type][combo]['total_bb_earnings'], 2)
                
                # Calculate averages for individual suit combos
                for suit_combo in analysis[hand_type][combo]['combos']:
                    suit_data = analysis[hand_type][combo]['combos'][suit_combo]
                    if suit_data['total_hands'] > 0:
                        suit_data['avg_bb_per_hand'] = round(
                            suit_data['total_bb_earnings'] / suit_data['total_hands'], 2
                        )
                        suit_data['total_bb_earnings'] = round(suit_data['total_bb_earnings'], 2)
        
        return analysis

    def calculate_ip_op_profitability(self, dataframe):
        ip_profitability = 0
        op_profitability = 0

        hu_flop_df = dataframe[dataframe['flop_HU_with_hero'] == True]

        for _, row in hu_flop_df.iterrows():
            if row['flop_Position']:  # Out of Position
                op_profitability += row['hand_result'] / row['bb_stake']
            else:  # In Position
                ip_profitability += row['hand_result'] / row['bb_stake']

        return round(ip_profitability, 2), round(op_profitability, 2)

    def _parse_card_rank(self, card_str):
        """Parse card string (e.g., 'As', 'Kd', 'Qh') and return rank value (A=14, K=13, Q=12, J=11, T=10, 9-2)"""
        if not card_str or not isinstance(card_str, str):
            return 0
        card_str = card_str.strip().upper()
        if len(card_str) < 2:
            return 0
        rank = card_str[0]
        rank_map = {'A': 14, 'K': 13, 'Q': 12, 'J': 11, 'T': 10}
        if rank in rank_map:
            return rank_map[rank]
        try:
            return int(rank)
        except ValueError:
            return 0

    def _get_board_cards_from_raw_hand(self, raw_hand):
        """Extract board cards from raw hand history - improved version"""
        board_cards = []
        if not raw_hand or not isinstance(raw_hand, str):
            return board_cards
        
        # Try to find all board cards by looking for the pattern in the summary section
        # Summary often has the complete board: "Board: [ Qd, 4d, 8c, 2h, 9s ]"
        if '** Summary **' in raw_hand:
            summary = raw_hand.split('** Summary **')[1]
            # Look for "Board:" pattern
            board_match = re.search(r'Board[:\s]+\[([^\]]+)\]', summary, re.IGNORECASE)
            if board_match:
                cards_str = board_match.group(1)
                cards = [c.strip() for c in cards_str.split(',') if c.strip()]
                if len(cards) >= 3:
                    return cards[:5]  # Return up to 5 cards (flop + turn + river)
        
        # Method 1: Extract flop cards
        if '** Dealing Flop **' in raw_hand:
            flop_section = raw_hand.split('** Dealing Flop **')[1]
            if '** Dealing Turn **' in flop_section:
                flop_section = flop_section.split('** Dealing Turn **')[0]
            elif '** Summary **' in flop_section:
                flop_section = flop_section.split('** Summary **')[0]
            
            # Look for pattern like "[ Qd, 4d, 8c ]" or ": [ Qd, 4d, 8c ]" or "** Dealing Flop ** : [ Qd, 4d, 8c ]"
            patterns = [
                r':\s*\[([^\]]+)\]',  # ": [ cards ]"
                r'\[([^\]]+)\]',      # "[ cards ]"
            ]
            
            for pattern in patterns:
                flop_match = re.search(pattern, flop_section, re.MULTILINE | re.DOTALL)
                if flop_match:
                    cards_str = flop_match.group(1)
                    cards = [c.strip() for c in cards_str.split(',') if c.strip()]
                    if len(cards) >= 3:
                        board_cards.extend(cards[:3])  # Flop has 3 cards
                        break
        
        # Method 2: Extract turn card (4th card total)
        if '** Dealing Turn **' in raw_hand:
            turn_section = raw_hand.split('** Dealing Turn **')[1]
            if '** Dealing River **' in turn_section:
                turn_section = turn_section.split('** Dealing River **')[0]
            elif '** Summary **' in turn_section:
                turn_section = turn_section.split('** Summary **')[0]
            
            # Look for all cards up to turn (should be 4 cards total)
            patterns = [
                r':\s*\[([^\]]+)\]',  # ": [ cards ]"
                r'\[([^\]]+)\]',      # "[ cards ]"
            ]
            
            for pattern in patterns:
                turn_match = re.search(pattern, turn_section, re.MULTILINE | re.DOTALL)
                if turn_match:
                    cards_str = turn_match.group(1)
                    cards = [c.strip() for c in cards_str.split(',') if c.strip()]
                    if len(cards) >= 4:
                        if len(board_cards) < 3:
                            # If we don't have flop cards yet, get all 4
                            board_cards = cards[:4]
                        else:
                            # We have flop, just add turn (4th card)
                            board_cards.append(cards[3])
                        break
        
        # Method 3: Extract river card (5th card total)
        if '** Dealing River **' in raw_hand:
            river_section = raw_hand.split('** Dealing River **')[1]
            if '** Summary **' in river_section:
                river_section = river_section.split('** Summary **')[0]
            
            patterns = [
                r':\s*\[([^\]]+)\]',  # ": [ cards ]"
                r'\[([^\]]+)\]',      # "[ cards ]"
            ]
            
            for pattern in patterns:
                river_match = re.search(pattern, river_section, re.MULTILINE | re.DOTALL)
                if river_match:
                    cards_str = river_match.group(1)
                    cards = [c.strip() for c in cards_str.split(',') if c.strip()]
                    if len(cards) >= 5:
                        if len(board_cards) < 4:
                            # If we don't have all cards yet, get all 5
                            board_cards = cards[:5]
                        else:
                            # We have flop+turn, just add river (5th card)
                            board_cards.append(cards[4])
                        break
        
        return board_cards

    def _get_street_cards(self, row, street):
        """Get cards for a specific street (flop, turn, river)"""
        cards = []
        
        # Try to get from structured columns first
        if street == 'flop' and 'flop_cards' in row:
            flop_cards = row['flop_cards']
            if flop_cards and flop_cards != 0 and not pd.isna(flop_cards):
                if isinstance(flop_cards, list):
                    cards = flop_cards[:3]
                elif isinstance(flop_cards, str):
                    # Parse string like "[ Qd, 4d, 8c ]"
                    match = re.search(r'\[([^\]]+)\]', flop_cards)
                    if match:
                        cards_str = match.group(1)
                        cards = [c.strip() for c in cards_str.split(',') if c.strip()][:3]
        elif street == 'turn' and 'turn_cards' in row:
            turn_cards = row['turn_cards']
            if turn_cards and turn_cards != 0 and not pd.isna(turn_cards):
                if isinstance(turn_cards, list):
                    cards = turn_cards[3:4] if len(turn_cards) >= 4 else []
                elif isinstance(turn_cards, str):
                    match = re.search(r'\[([^\]]+)\]', turn_cards)
                    if match:
                        cards_str = match.group(1)
                        all_cards = [c.strip() for c in cards_str.split(',') if c.strip()]
                        if len(all_cards) >= 4:
                            cards = [all_cards[3]]
        elif street == 'river' and 'river_cards' in row:
            river_cards = row['river_cards']
            if river_cards and river_cards != 0 and not pd.isna(river_cards):
                if isinstance(river_cards, list):
                    cards = river_cards[4:5] if len(river_cards) >= 5 else []
                elif isinstance(river_cards, str):
                    match = re.search(r'\[([^\]]+)\]', river_cards)
                    if match:
                        cards_str = match.group(1)
                        all_cards = [c.strip() for c in cards_str.split(',') if c.strip()]
                        if len(all_cards) >= 5:
                            cards = [all_cards[4]]
        
        # Fallback to raw hand parsing
        if not cards:
            raw_hand = row.get('Raw Hand', '')
            if raw_hand:
                board_cards = self._get_board_cards_from_raw_hand(raw_hand)
                if street == 'flop' and len(board_cards) >= 3:
                    cards = board_cards[:3]
                elif street == 'turn' and len(board_cards) >= 4:
                    cards = [board_cards[3]]
                elif street == 'river' and len(board_cards) >= 5:
                    cards = [board_cards[4]]
        
        return cards

    def calculate_street_high_card_analysis(self, dataframe, street):
        """Calculate high card analysis for a specific street (flop, turn, river)"""
        analysis = {}
        
        # Filter to hands that reached this street - check multiple sources
        street_mask = pd.Series([False] * len(dataframe), index=dataframe.index)
        
        # Method 1: Check main flop column
        if street == 'flop' and 'flop' in dataframe.columns:
            street_mask = street_mask | (dataframe['flop'] == True)
        
        # Method 2: Check if street cards exist
        if street == 'turn' and 'turn_cards' in dataframe.columns:
            street_mask = street_mask | ((dataframe['turn_cards'] != 0) & (dataframe['turn_cards'].notna()))
        elif street == 'river' and 'river_cards' in dataframe.columns:
            street_mask = street_mask | ((dataframe['river_cards'] != 0) & (dataframe['river_cards'].notna()))
        
        # Method 3: Check HU columns (for heads-up hands)
        if street == 'turn' and 'turn_HU_with_hero' in dataframe.columns:
            street_mask = street_mask | (dataframe['turn_HU_with_hero'] == True)
        elif street == 'river' and 'river_HU_with_hero' in dataframe.columns:
            street_mask = street_mask | (dataframe['river_HU_with_hero'] == True)
        
        # Method 4: Check Raw Hand for street markers (most reliable)
        def has_street_in_raw_hand(raw_hand, street_name):
            if not raw_hand or not isinstance(raw_hand, str):
                return False
            if street_name == 'flop':
                return '** Dealing Flop **' in raw_hand
            elif street_name == 'turn':
                return '** Dealing Turn **' in raw_hand
            elif street_name == 'river':
                return '** Dealing River **' in raw_hand
            return False
        
        if 'Raw Hand' in dataframe.columns:
            street_mask = street_mask | dataframe['Raw Hand'].apply(lambda x: has_street_in_raw_hand(x, street))
        
        street_df = dataframe[street_mask].copy()
        
        rank_names = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: 'T', 9: '9', 8: '8', 7: '7', 6: '6', 5: '5', 4: '4', 3: '3', 2: '2'}
        
        for _, row in street_df.iterrows():
            cards = self._get_street_cards(row, street)
            
            # If we couldn't get cards from structured data, try raw hand parsing
            if not cards:
                raw_hand = row.get('Raw Hand', '')
                if raw_hand:
                    board_cards = self._get_board_cards_from_raw_hand(raw_hand)
                    if street == 'flop' and len(board_cards) >= 3:
                        cards = board_cards[:3]
                    elif street == 'turn' and len(board_cards) >= 4:
                        cards = [board_cards[3]]
                    elif street == 'river' and len(board_cards) >= 5:
                        cards = [board_cards[4]]
            
            if not cards:
                continue
            
            # Find highest card rank on this street
            max_rank = 0
            for card in cards:
                rank = self._parse_card_rank(card)
                max_rank = max(max_rank, rank)
            
            if max_rank == 0:
                continue
            
            rank_name = rank_names.get(max_rank, str(max_rank))
            high_card_label = f'{rank_name} High'
            
            if high_card_label not in analysis:
                analysis[high_card_label] = {
                    'total_hands': 0,
                    'total_bb_earnings': 0.0,
                    'avg_bb_per_hand': 0.0
                }
            
            bb_earnings = row['hand_result'] / row['bb_stake']
            analysis[high_card_label]['total_hands'] += 1
            analysis[high_card_label]['total_bb_earnings'] += bb_earnings
        
        # Calculate averages
        for label in analysis:
            if analysis[label]['total_hands'] > 0:
                analysis[label]['avg_bb_per_hand'] = round(
                    analysis[label]['total_bb_earnings'] / analysis[label]['total_hands'], 2
                )
                analysis[label]['total_bb_earnings'] = round(analysis[label]['total_bb_earnings'], 2)
        
        return analysis

    def calculate_board_high_card_analysis(self, dataframe):
        """Calculate board high card analysis (highest card on the entire board)"""
        analysis = {}
        
        # Filter to hands that reached flop - check multiple sources
        flop_mask = pd.Series([False] * len(dataframe), index=dataframe.index)
        
        # Method 1: Check main flop column
        if 'flop' in dataframe.columns:
            flop_mask = flop_mask | (dataframe['flop'] == True)
        
        # Method 2: Check Raw Hand for flop marker (most reliable)
        def has_flop_in_raw_hand(raw_hand):
            if not raw_hand or not isinstance(raw_hand, str):
                return False
            return '** Dealing Flop **' in raw_hand
        
        if 'Raw Hand' in dataframe.columns:
            flop_mask = flop_mask | dataframe['Raw Hand'].apply(has_flop_in_raw_hand)
        
        flop_df = dataframe[flop_mask].copy()
        
        rank_names = {14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: 'T', 9: '9', 8: '8', 7: '7', 6: '6', 5: '5', 4: '4', 3: '3', 2: '2'}
        
        for _, row in flop_df.iterrows():
            # Get all board cards
            raw_hand = row.get('Raw Hand', '')
            board_cards = self._get_board_cards_from_raw_hand(raw_hand)
            
            if not board_cards:
                continue
            
            # Find highest card rank on the board
            max_rank = 0
            for card in board_cards:
                rank = self._parse_card_rank(card)
                max_rank = max(max_rank, rank)
            
            if max_rank == 0:
                continue
            
            rank_name = rank_names.get(max_rank, str(max_rank))
            high_card_label = f'{rank_name} High Board'
            
            if high_card_label not in analysis:
                analysis[high_card_label] = {
                    'total_hands': 0,
                    'total_bb_earnings': 0.0,
                    'avg_bb_per_hand': 0.0
                }
            
            bb_earnings = row['hand_result'] / row['bb_stake']
            analysis[high_card_label]['total_hands'] += 1
            analysis[high_card_label]['total_bb_earnings'] += bb_earnings
        
        # Calculate averages
        for label in analysis:
            if analysis[label]['total_hands'] > 0:
                analysis[label]['avg_bb_per_hand'] = round(
                    analysis[label]['total_bb_earnings'] / analysis[label]['total_hands'], 2
                )
                analysis[label]['total_bb_earnings'] = round(analysis[label]['total_bb_earnings'], 2)
        
        return analysis

    def calculate_street_positional_matchups(self, dataframe, street):
        """Calculate positional matchups for a specific street (flop, turn, river)
        Returns dict with matchup keys like 'UTG vs CO' and data: total_hands, total_bb_earnings, total_earnings, avg_bb_per_hand
        """
        matchups = {}
        
        # Filter to hands that reached this street - check multiple sources
        street_mask = pd.Series([False] * len(dataframe), index=dataframe.index)
        
        # Method 1: Check main flop column
        if street == 'flop' and 'flop' in dataframe.columns:
            street_mask = street_mask | (dataframe['flop'] == True)
        
        # Method 2: Check if street cards exist
        if street == 'turn' and 'turn_cards' in dataframe.columns:
            street_mask = street_mask | ((dataframe['turn_cards'] != 0) & (dataframe['turn_cards'].notna()))
        elif street == 'river' and 'river_cards' in dataframe.columns:
            street_mask = street_mask | ((dataframe['river_cards'] != 0) & (dataframe['river_cards'].notna()))
        
        # Method 3: Check HU columns (for heads-up hands)
        if street == 'turn' and 'turn_HU_with_hero' in dataframe.columns:
            street_mask = street_mask | (dataframe['turn_HU_with_hero'] == True)
        elif street == 'river' and 'river_HU_with_hero' in dataframe.columns:
            street_mask = street_mask | (dataframe['river_HU_with_hero'] == True)
        
        # Method 4: Check Raw Hand for street markers (most reliable)
        def has_street_in_raw_hand(raw_hand, street_name):
            if not raw_hand or not isinstance(raw_hand, str):
                return False
            if street_name == 'flop':
                return '** Dealing Flop **' in raw_hand
            elif street_name == 'turn':
                return '** Dealing Turn **' in raw_hand
            elif street_name == 'river':
                return '** Dealing River **' in raw_hand
            return False
        
        if 'Raw Hand' in dataframe.columns:
            street_mask = street_mask | dataframe['Raw Hand'].apply(lambda x: has_street_in_raw_hand(x, street))
        
        street_df = dataframe[street_mask].copy()
        
        for _, row in street_df.iterrows():
            hero_position = row.get('position', 'Unknown')
            # Valid positions: UTG, MP, CO, BTN, SB, BB (and HJ for 5-handed)
            valid_positions = ['UTG', 'HJ', 'MP', 'CO', 'BTN', 'SB', 'BB']
            if hero_position == 'Unknown' or hero_position not in valid_positions:
                continue
            
            # Get villain position from raw hand - find who raised preflop or who we're heads-up against
            raw_hand = row.get('Raw Hand', '')
            villain_position = self._get_villain_position_from_raw_hand(raw_hand, hero_position)
            
            if not villain_position or villain_position not in valid_positions:
                continue
            
            matchup_key = f'{hero_position} vs {villain_position}'
            
            if matchup_key not in matchups:
                matchups[matchup_key] = {
                    'total_hands': 0,
                    'total_bb_earnings': 0.0,
                    'total_earnings': 0.0,
                    'avg_bb_per_hand': 0.0
                }
            
            bb_earnings = row['hand_result'] / row['bb_stake']
            earnings = row['hand_result']
            
            matchups[matchup_key]['total_hands'] += 1
            matchups[matchup_key]['total_bb_earnings'] += bb_earnings
            matchups[matchup_key]['total_earnings'] += earnings
        
        # Calculate averages
        for matchup_key in matchups:
            if matchups[matchup_key]['total_hands'] > 0:
                matchups[matchup_key]['avg_bb_per_hand'] = round(
                    matchups[matchup_key]['total_bb_earnings'] / matchups[matchup_key]['total_hands'], 2
                )
                matchups[matchup_key]['total_bb_earnings'] = round(matchups[matchup_key]['total_bb_earnings'], 2)
                matchups[matchup_key]['total_earnings'] = round(matchups[matchup_key]['total_earnings'], 2)
        
        return matchups
    
    def calculate_overall_positional_matchups(self, dataframe):
        """Calculate overall positional matchups grouped by pot type (RFI, 3-bet, 4-bet)"""
        matchups = {
            'RFI Pots': {},
            '3-Bet Pots': {},
            '4-Bet Pots': {},
            '5-Bet Pots': {},
            'Limp Pots': {},
            'RFI Multiway Pots': {},
            '3-Bet Multiway Pots': {},
            '4-Bet Multiway Pots': {}
        }

        def _preflop_action_counts(raw_hand):
            """Return (raise_count, call_after_raise, call_after_3bet, call_after_4bet, call_after_5bet, limp_detected)."""
            if not raw_hand or not isinstance(raw_hand, str):
                return 0, 0, 0, 0, 0, False

            preflop_section = raw_hand
            if '** Dealing down cards **' in raw_hand:
                preflop_section = raw_hand.split('** Dealing down cards **')[1]
            if '** Dealing Flop **' in preflop_section:
                preflop_section = preflop_section.split('** Dealing Flop **')[0]
            elif '** Summary **' in preflop_section:
                preflop_section = preflop_section.split('** Summary **')[0]

            lines = [line.strip() for line in preflop_section.split('\n') if line.strip()]
            raise_count = 0
            saw_raise = False
            saw_3bet = False
            saw_4bet = False
            saw_5bet = False
            call_after_raise = 0
            call_after_3bet = 0
            call_after_4bet = 0
            call_after_5bet = 0
            limp_detected = False

            for line in lines:
                lower_line = line.lower()
                if ' posts ' in lower_line:
                    continue
                if ' raises ' in lower_line or ' bets ' in lower_line:
                    raise_count += 1
                    saw_raise = True
                    if raise_count >= 2:
                        saw_3bet = True
                    if raise_count >= 3:
                        saw_4bet = True
                    if raise_count >= 4:
                        saw_5bet = True
                    continue
                if ' calls ' in lower_line:
                    if not saw_raise:
                        limp_detected = True
                    elif not saw_3bet:
                        call_after_raise += 1
                    elif not saw_4bet:
                        call_after_3bet += 1
                    elif not saw_5bet:
                        call_after_4bet += 1
                    else:
                        call_after_5bet += 1

            return raise_count, call_after_raise, call_after_3bet, call_after_4bet, call_after_5bet, limp_detected

        def is_heads_up_srp(raw_hand):
            """Single-raised pot: no limps, one raise, one call (heads-up)."""
            raise_count, call_after_raise, _, _, _, limp_detected = _preflop_action_counts(raw_hand)
            return (raise_count == 1) and (call_after_raise == 1) and (not limp_detected)

        def is_heads_up_3bet(raw_hand):
            """3-bet pot: no limps, one open raise, one 3-bet, one caller of 3-bet (heads-up)."""
            raise_count, _, call_after_3bet, _, _, limp_detected = _preflop_action_counts(raw_hand)
            return (raise_count == 2) and (call_after_3bet == 1) and (not limp_detected)

        def is_heads_up_4bet(raw_hand):
            """4-bet pot: no limps, one open raise, one 3-bet, one 4-bet, one caller of 4-bet (heads-up)."""
            raise_count, _, _, call_after_4bet, _, limp_detected = _preflop_action_counts(raw_hand)
            return (raise_count == 3) and (call_after_4bet == 1) and (not limp_detected)
        
        def is_heads_up_5bet(raw_hand):
            """5-bet pot: no limps, one open raise, one 3-bet, one 4-bet, one 5-bet, one caller of 5-bet (heads-up)."""
            raise_count, _, _, _, call_after_5bet, limp_detected = _preflop_action_counts(raw_hand)
            return (raise_count == 4) and (call_after_5bet == 1) and (not limp_detected)

        def is_heads_up_limp(raw_hand):
            """Limped pot: no raises, exactly one limp (heads-up, BB checks)."""
            raise_count, _, _, _, _, limp_detected = _preflop_action_counts(raw_hand)
            if raise_count != 0 or not limp_detected:
                return False

            preflop_section = raw_hand
            if '** Dealing down cards **' in raw_hand:
                preflop_section = raw_hand.split('** Dealing down cards **')[1]
            if '** Dealing Flop **' in preflop_section:
                preflop_section = preflop_section.split('** Dealing Flop **')[0]
            elif '** Summary **' in preflop_section:
                preflop_section = preflop_section.split('** Summary **')[0]

            lines = [line.strip() for line in preflop_section.split('\n') if line.strip()]
            limp_calls = 0
            for line in lines:
                lower_line = line.lower()
                if ' posts ' in lower_line:
                    continue
                if ' calls ' in lower_line:
                    limp_calls += 1
                if ' raises ' in lower_line or ' bets ' in lower_line:
                    return False

            return limp_calls == 1
        for _, row in dataframe.iterrows():
            hero_position = row.get('position', 'Unknown')
            # Valid positions: UTG, MP, CO, BTN, SB, BB (and HJ for 5-handed)
            valid_positions = ['UTG', 'HJ', 'MP', 'CO', 'BTN', 'SB', 'BB']
            if hero_position == 'Unknown' or hero_position not in valid_positions:
                continue
            
            raw_hand = row.get('Raw Hand', '')
            if not raw_hand:
                continue
                
            villain_position = self._get_villain_position_from_raw_hand(raw_hand, hero_position)
            
            # Determine pot type from preflop action
            pot_type = None
            is_multiway = False
            
            # Determine pot type from raw hand (not Hero-specific)
            if is_heads_up_5bet(raw_hand):
                pot_type = '5-Bet Pots'
            elif is_heads_up_4bet(raw_hand):
                pot_type = '4-Bet Pots'
            elif is_heads_up_3bet(raw_hand):
                pot_type = '3-Bet Pots'
            elif is_heads_up_srp(raw_hand):
                pot_type = 'RFI Pots'
            elif is_heads_up_limp(raw_hand):
                pot_type = 'Limp Pots'
            else:
                # Not a valid SRP/3-bet/4-bet for matchups
                continue

            if pot_type == '5-Bet Pots':
                hero_saw_flop = row.get('hero_saw_flop', False)
                hero_active_flop = row.get('hero_is_active_on_flop', False)
                if not (hero_saw_flop or hero_active_flop):
                    continue

            if pot_type == 'Limp Pots':
                hero_saw_flop = row.get('hero_saw_flop', False)
                hero_active_flop = row.get('hero_is_active_on_flop', False)
                if not (hero_saw_flop or hero_active_flop):
                    continue
            
            # Check if multiway (more than 2 players saw flop) and get all opponent positions
            opponent_positions = []
            is_multiway = False
            
            if '** Dealing Flop **' in raw_hand or '** Summary **' in raw_hand:
                preflop_section = raw_hand.split('** Dealing Flop **')[0] if '** Dealing Flop **' in raw_hand else raw_hand.split('** Summary **')[0]
                
                # Get position map to find all opponent positions
                try:
                    if 'Total number of players :' in raw_hand:
                        total_players = int(raw_hand.split('Total number of players :')[1].split('/')[0].strip())
                        button_seat = self.get_button_seat(raw_hand)
                        seat_info = self.get_seat_info(raw_hand)
                        if seat_info:
                            position_map = self.calculate_positions(seat_info, button_seat, total_players)
                            
                            # Get all players who acted preflop (excluding Hero)
                            players_who_acted = set()
                            for line in preflop_section.split('\n'):
                                line = line.strip()
                                if not line:
                                    continue
                                if any(word in line.lower() for word in ['calls', 'raises', 'bets', 'checks', 'all-in']):
                                    # Extract player name
                                    if ':' in line and 'Seat' in line:
                                        try:
                                            player_part = line.split(':')[1].strip()
                                            player_name = player_part.split()[0] if player_part.split() else None
                                            if player_name and player_name != 'Hero':
                                                players_who_acted.add(player_name)
                                        except:
                                            pass
                                    else:
                                        parts = line.split()
                                        if parts:
                                            potential_name = parts[0]
                                            if potential_name and potential_name != 'Hero':
                                                players_who_acted.add(potential_name)
                            
                            # Get positions of all opponents who acted
                            for player_name in players_who_acted:
                                if player_name in position_map:
                                    opp_position = position_map[player_name]
                                    if opp_position in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
                                        opponent_positions.append(opp_position)
                            
                            # Remove duplicates and sort
                            opponent_positions = sorted(list(set(opponent_positions)))
                            
                            # Check if multiway (3+ players total who saw flop)
                            # Count players who actually saw the flop, not just acted preflop
                            players_saw_flop = set()
                            if '** Dealing Flop **' in raw_hand:
                                flop_section = raw_hand.split('** Dealing Flop **')[1] if '** Dealing Flop **' in raw_hand else ''
                                # Check who was still in the hand at flop
                                for line in flop_section.split('\n'):
                                    line = line.strip()
                                    if not line or '** Dealing Turn **' in line or '** Summary **' in line:
                                        break
                                    # Look for player actions on flop
                                    if any(word in line.lower() for word in ['bets', 'checks', 'calls', 'raises', 'folds']):
                                        # Extract player name
                                        if ':' in line and 'Seat' in line:
                                            try:
                                                player_part = line.split(':')[1].strip()
                                                player_name = player_part.split()[0] if player_part.split() else None
                                                if player_name and player_name in position_map:
                                                    players_saw_flop.add(player_name)
                                            except:
                                                pass
                                        else:
                                            parts = line.split()
                                            if parts:
                                                potential_name = parts[0]
                                                if potential_name and potential_name in position_map:
                                                    players_saw_flop.add(potential_name)
                            
                            # Add Hero to count
                            total_players_saw_flop = len(players_saw_flop) + 1  # +1 for Hero
                            
                            # If no flop action found, use preflop count as fallback
                            if total_players_saw_flop <= 1:
                                total_players_saw_flop = len(players_who_acted) + 1
                            
                            # Multiway = 3+ players (Hero + 2+ opponents)
                            if total_players_saw_flop >= 3 and len(opponent_positions) >= 2:
                                is_multiway = True
                                if 'Multiway' not in pot_type:
                                    pot_type = pot_type.replace('Pots', 'Multiway Pots')
                            else:
                                # Heads-up pot - ensure it's not marked as multiway
                                is_multiway = False
                                if 'Multiway' in pot_type:
                                    pot_type = pot_type.replace('Multiway Pots', 'Pots')
                except Exception as e:
                    print(f"Error extracting opponent positions: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Create matchup key based on whether it's multiway or heads-up
            matchup_key = None

            # Heads-up limp pots must always include the BB (limper + BB check)
            if pot_type == 'Limp Pots':
                if is_multiway:
                    continue
                try:
                    if 'Total number of players :' in raw_hand:
                        total_players = int(raw_hand.split('Total number of players :')[1].split('/')[0].strip())
                        button_seat = self.get_button_seat(raw_hand)
                        seat_info = self.get_seat_info(raw_hand)
                        if seat_info:
                            position_map = self.calculate_positions(seat_info, button_seat, total_players)
                            preflop_section = raw_hand
                            if '** Dealing down cards **' in raw_hand:
                                preflop_section = raw_hand.split('** Dealing down cards **')[1]
                            if '** Dealing Flop **' in preflop_section:
                                preflop_section = preflop_section.split('** Dealing Flop **')[0]
                            elif '** Summary **' in preflop_section:
                                preflop_section = preflop_section.split('** Summary **')[0]

                            limper_name = None
                            for line in preflop_section.split('\n'):
                                line = line.strip()
                                if not line:
                                    continue
                                lower_line = line.lower()
                                if ' posts ' in lower_line:
                                    continue
                                if ' calls ' in lower_line:
                                    parts = line.split()
                                    if parts:
                                        limper_name = parts[0]
                                        break

                            if hero_position == 'BB':
                                if limper_name and limper_name in position_map:
                                    villain_position = position_map.get(limper_name)
                            else:
                                villain_position = 'BB'
                except Exception:
                    pass

                if hero_position != 'BB' and villain_position != 'BB':
                    continue
            
            if is_multiway and opponent_positions and len(opponent_positions) >= 2:
                # Multiway pot (3+ players) - show all opponent positions: "UTG vs CO and BB"
                opponent_str = ' and '.join(opponent_positions)
                matchup_key = f'{hero_position} vs {opponent_str}'
            elif not is_multiway:
                # Heads-up pot - use villain position
                if villain_position and villain_position in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
                    # Skip if same position (invalid matchup)
                    if hero_position != villain_position:
                        matchup_key = f'{hero_position} vs {villain_position}'
            
            # Skip if no valid matchup key
            if not matchup_key:
                continue
            
            # Ensure pot_type exists in matchups dict
            if pot_type not in matchups:
                matchups[pot_type] = {}
            
            if matchup_key not in matchups[pot_type]:
                matchups[pot_type][matchup_key] = {
                    'total_hands': 0,
                    'total_bb_earnings': 0.0,
                    'total_earnings': 0.0,
                    'avg_bb_per_hand': 0.0
                }
            
            # Calculate BB earnings safely
            try:
                bb_stake = row.get('bb_stake', 1.0)
                if bb_stake == 0 or bb_stake is None:
                    bb_stake = 1.0
                hand_result = row.get('hand_result', 0.0)
                if hand_result is None:
                    hand_result = 0.0
                bb_earnings = float(hand_result) / float(bb_stake)
                earnings = float(hand_result)
            except (ZeroDivisionError, TypeError, KeyError, ValueError) as e:
                print(f"Error calculating BB earnings: {e}, hand_result={row.get('hand_result')}, bb_stake={row.get('bb_stake')}")
                bb_earnings = 0.0
                earnings = 0.0
            
            # Add the hand data
            matchups[pot_type][matchup_key]['total_hands'] += 1
            matchups[pot_type][matchup_key]['total_bb_earnings'] += bb_earnings
            matchups[pot_type][matchup_key]['total_earnings'] += earnings
        
        # Calculate averages and round values
        for pot_type in list(matchups.keys()):
            if not matchups[pot_type]:
                continue
            
            for matchup_key in matchups[pot_type]:
                matchup_data = matchups[pot_type][matchup_key]
                if matchup_data['total_hands'] > 0:
                    matchup_data['avg_bb_per_hand'] = round(
                        matchup_data['total_bb_earnings'] / matchup_data['total_hands'], 2
                    )
                matchup_data['total_bb_earnings'] = round(matchup_data['total_bb_earnings'], 2)
                matchup_data['total_earnings'] = round(matchup_data['total_earnings'], 2)
        
        # Debug: Print summary of what was generated
        total_hands = sum(sum(m.get('total_hands', 0) for m in pot.values()) for pot in matchups.values())
        print(f"Positional matchups generated: {total_hands} total hands across {len([p for p in matchups.values() if p])} pot types")
        for pot_type, pot_data in matchups.items():
            if pot_data:
                pot_hands = sum(m.get('total_hands', 0) for m in pot_data.values())
                if pot_hands > 0:
                    print(f"  {pot_type}: {pot_hands} hands, {len(pot_data)} matchups")
        
        # Remove completely empty pot types only if ALL are empty
        # But keep at least one structure for the template
        non_empty_pot_types = {k: v for k, v in matchups.items() if v and isinstance(v, dict) and len(v) > 0}
        if non_empty_pot_types:
            return non_empty_pot_types
        else:
            # Return empty dict - template will handle this gracefully
            return {}
    
    def _get_villain_position_from_raw_hand(self, raw_hand, hero_position):
        """Extract villain position from raw hand - find the opponent who we're heads-up against"""
        if not raw_hand or not isinstance(raw_hand, str):
            return None
        
        try:
            # Use the same methods that calculate hero position to get all positions
            if 'Total number of players :' not in raw_hand:
                return None
                
            total_players = int(raw_hand.split('Total number of players :')[1].split('/')[0].strip())
            button_seat = self.get_button_seat(raw_hand)
            seat_info = self.get_seat_info(raw_hand)  # Returns list of (seat_num, player_name) tuples
            
            if not seat_info:
                return None
                
            position_map = self.calculate_positions(seat_info, button_seat, total_players)
            
            if not position_map:
                return None
            
            # Get all player names from seat info (excluding Hero)
            all_player_names = {name for _, name in seat_info if name != 'Hero'}
            
            # Find the villain - the other player in heads-up pots
            # Look for players who acted preflop (not Hero)
            villain_player_name = None
            
            # Extract preflop section
            if '** Dealing Flop **' in raw_hand:
                preflop_section = raw_hand.split('** Dealing Flop **')[0]
            elif '** Summary **' in raw_hand:
                preflop_section = raw_hand.split('** Summary **')[0]
            else:
                preflop_section = raw_hand  # Use entire hand if no markers found
            
            # Find who raised or called (the villain)
            # Look for action lines with player names (not Hero)
            players_who_acted = set()
            action_words = ['raises', 'calls', 'bets', 'folds', 'checks', 'all-in']
            
            for line in preflop_section.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Skip lines that are just Hero actions (but don't skip lines that mention Hero and others)
                if line.startswith('Hero ') and any(word in line.lower() for word in action_words):
                    continue
                
                # Look for patterns like "Seat X: PlayerName raises" or "PlayerName calls"
                line_lower = line.lower()
                if any(word in line_lower for word in action_words):
                    # Extract player name from line
                    # Format is usually "Seat X: PlayerName action" or "PlayerName action"
                    if ':' in line and 'Seat' in line:
                        # Format: "Seat X: PlayerName action"
                        try:
                            player_part = line.split(':')[1].strip()
                            parts = player_part.split()
                            if parts:
                                player_name = parts[0]
                                # Validate it's a known player name
                                if player_name in all_player_names:
                                    players_who_acted.add(player_name)
                        except:
                            pass
                    else:
                        # Try to extract from line directly (e.g., "PlayerName raises")
                        parts = line.split()
                        if parts and len(parts) > 0:
                            potential_name = parts[0]
                            # Validate it's a known player name and not an action word
                            if (potential_name in all_player_names and 
                                potential_name.lower() not in action_words):
                                players_who_acted.add(potential_name)
            
            # If we found players who acted, prioritize those who raised/called (not just folded)
            # First, try to find someone who raised or called (more likely to be the villain)
            priority_players = []
            for line in preflop_section.split('\n'):
                line = line.strip()
                if not line or line.startswith('Hero '):
                    continue
                for player_name in players_who_acted:
                    if line.startswith(player_name + ' ') and ('raises' in line.lower() or 'calls' in line.lower()):
                        if player_name in position_map:
                            priority_players.append(player_name)
            
            # Use priority players first, then any player who acted
            if priority_players:
                villain_player_name = priority_players[0]
            elif players_who_acted:
                for player_name in players_who_acted:
                    if player_name in position_map:
                        villain_player_name = player_name
                        break
            
            # Fallback: find any player that's not Hero (for hands where Hero folded early)
            if not villain_player_name:
                for seat_num, player_name in seat_info:
                    if player_name != 'Hero' and player_name in position_map:
                        villain_player_name = player_name
                        break
            
            if villain_player_name and villain_player_name in position_map:
                return position_map[villain_player_name]
            
            # If we still don't have villain, try a different approach:
            # For heads-up pots, the villain is usually the other player
            # Check summary for who won/lost (they must have been involved)
            if '** Summary **' in raw_hand:
                summary = raw_hand.split('** Summary **')[1]
                # Look for player names in summary who actually bet (not Hero)
                for seat_num, player_name in seat_info:
                    if player_name != 'Hero' and player_name in summary:
                        # Check if they actually bet (not just folded)
                        if 'bet' in summary.lower() and player_name in summary:
                            if player_name in position_map:
                                return position_map[player_name]
            
        except Exception as e:
            # Log the error so we can see what's failing
            print(f"Error in _get_villain_position_from_raw_hand: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        return None
    
    def calculate_biggest_hands(self, dataframe):
        """Calculate biggest winning and losing hands"""
        biggest_hands = {
            'biggest_wins': [],
            'biggest_losses': []
        }
        
        # Get hands with pot size information
        hands_with_pots = []
        
        for _, row in dataframe.iterrows():
            raw_hand = row.get('Raw Hand', '')
            hand_result = row.get('hand_result', 0)
            bb_stake = row.get('bb_stake', 0.25)
            bb_earnings = hand_result / bb_stake if bb_stake > 0 else 0
            
            # Try to extract pot size from raw hand or use calculated pot
            pot_size = 0
            if raw_hand and '** Summary **' in raw_hand:
                # Try to extract pot size from summary
                summary_section = raw_hand.split('** Summary **')[1]
                pot_match = re.search(r'pot.*?(\d+\.?\d*)', summary_section, re.IGNORECASE)
                if pot_match:
                    try:
                        pot_size = float(pot_match.group(1))
                    except:
                        pass
            
            # If we couldn't get pot size, estimate from BB stake
            if pot_size == 0:
                pot_size = abs(hand_result) * 2  # Rough estimate
            
            hands_with_pots.append({
                'hand_result': hand_result,
                'bb_earnings': bb_earnings,
                'pot_size': pot_size,
                'raw_hand': raw_hand,
                'formatted_hand': self._format_hand_for_display(raw_hand) if raw_hand else None
            })
        
        # Sort by hand_result (positive = wins, negative = losses)
        hands_with_pots.sort(key=lambda x: x['hand_result'], reverse=True)
        
        # Get top 3 wins
        wins = [h for h in hands_with_pots if h['hand_result'] > 0]
        biggest_hands['biggest_wins'] = wins[:3]
        
        # Get top 3 losses (most negative)
        losses = [h for h in hands_with_pots if h['hand_result'] < 0]
        losses.sort(key=lambda x: x['hand_result'])  # Sort ascending (most negative first)
        biggest_hands['biggest_losses'] = losses[:3]
        
        return biggest_hands
    
    def _format_hand_for_display(self, raw_hand):
        """Comprehensively format raw hand history for display in biggest hands section"""
        if not raw_hand or not isinstance(raw_hand, str):
            return None
        
        formatted = {
            'raw_hand': raw_hand,
            'table_info': {},
            'seats': [],
            'hero_cards': [],
            'preflop_action': [],
            'flop_cards': [],
            'flop_action': [],
            'turn_card': None,
            'turn_action': [],
            'river_card': None,
            'river_action': [],
            'player_hands': [],
            'summary': []
        }
        
        # Parse table info
        table_match = re.search(r'Table\s+([^\n]+)', raw_hand)
        if table_match:
            formatted['table_info']['table_name'] = table_match.group(1).strip()
        
        stakes_match = re.search(r'(\$\d+\.?\d*/\$\d+\.?\d*)', raw_hand)
        if stakes_match:
            formatted['table_info']['stakes'] = stakes_match.group(1)
        
        date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', raw_hand)
        if date_match:
            formatted['table_info']['date'] = date_match.group(1)
        
        # Parse seats
        seat_pattern = r'Seat\s+(\d+):\s+([^(]+)\s+\((\$[\d.]+)\s+in\s+chips\)'
        for match in re.finditer(seat_pattern, raw_hand):
            seat_num = match.group(1)
            player_name = match.group(2).strip()
            stack = match.group(3)
            
            # Get button seat
            button_seat = self.get_button_seat(raw_hand)
            is_button = (button_seat and str(button_seat) == seat_num)
            is_hero = (player_name == 'Hero')
            
            # Get position
            seat_info = self.get_seat_info(raw_hand)
            total_players_match = re.search(r'Total number of players\s*:\s*(\d+)', raw_hand)
            total_players = int(total_players_match.group(1)) if total_players_match else 6
            position_map = self.calculate_positions(seat_info, button_seat, total_players)
            position = position_map.get(player_name, 'Unknown')
            
            formatted['seats'].append({
                'seat': seat_num,
                'player': player_name,
                'stack': stack.replace('$', ''),
                'position': position,
                'is_hero': is_hero,
                'is_button': is_button
            })
        
        # Parse hero cards
        hero_match = re.search(r'Hero.*?\[([^\]]+)\]', raw_hand)
        if hero_match:
            cards_str = hero_match.group(1)
            formatted['hero_cards'] = [self._format_card_for_display(c.strip()) for c in cards_str.split(',') if c.strip()]
        
        # Parse preflop action
        if '** Dealing down cards **' in raw_hand and '** Dealing Flop **' in raw_hand:
            preflop_section = raw_hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0]
            for line in preflop_section.split('\n'):
                line = line.strip()
                if line and ('raises' in line.lower() or 'calls' in line.lower() or 'folds' in line.lower() or 'checks' in line.lower() or 'bets' in line.lower() or 'all-in' in line.lower()):
                    formatted['preflop_action'].append(line)
        
        # Parse flop
        flop_match = re.search(r'\*\* Dealing Flop \*\*.*?\[([^\]]+)\]', raw_hand, re.DOTALL)
        if flop_match:
            cards_str = flop_match.group(1)
            formatted['flop_cards'] = [self._format_card_for_display(c.strip()) for c in cards_str.split(',') if c.strip()][:3]
            
            # Parse flop action
            if '** Dealing Turn **' in raw_hand:
                flop_section = raw_hand.split('** Dealing Flop **')[1].split('** Dealing Turn **')[0]
            elif '** Dealing River **' in raw_hand:
                flop_section = raw_hand.split('** Dealing Flop **')[1].split('** Dealing River **')[0]
            elif '** Summary **' in raw_hand:
                flop_section = raw_hand.split('** Dealing Flop **')[1].split('** Summary **')[0]
            else:
                flop_section = raw_hand.split('** Dealing Flop **')[1] if '** Dealing Flop **' in raw_hand else ''
            
            for line in flop_section.split('\n'):
                line = line.strip()
                if line and ('raises' in line.lower() or 'calls' in line.lower() or 'folds' in line.lower() or 'checks' in line.lower() or 'bets' in line.lower() or 'all-in' in line.lower()):
                    formatted['flop_action'].append(line)
        
        # Parse turn
        turn_match = re.search(r'\*\* Dealing Turn \*\*.*?\[([^\]]+)\]', raw_hand, re.DOTALL)
        if turn_match:
            cards_str = turn_match.group(1)
            cards = [c.strip() for c in cards_str.split(',') if c.strip()]
            if len(cards) >= 4:
                formatted['turn_card'] = self._format_card_for_display(cards[3])
            
            # Parse turn action
            if '** Dealing River **' in raw_hand:
                turn_section = raw_hand.split('** Dealing Turn **')[1].split('** Dealing River **')[0]
            elif '** Summary **' in raw_hand:
                turn_section = raw_hand.split('** Dealing Turn **')[1].split('** Summary **')[0]
            else:
                turn_section = raw_hand.split('** Dealing Turn **')[1] if '** Dealing Turn **' in raw_hand else ''
            
            for line in turn_section.split('\n'):
                line = line.strip()
                if line and ('raises' in line.lower() or 'calls' in line.lower() or 'folds' in line.lower() or 'checks' in line.lower() or 'bets' in line.lower() or 'all-in' in line.lower()):
                    formatted['turn_action'].append(line)
        
        # Parse river
        river_match = re.search(r'\*\* Dealing River \*\*.*?\[([^\]]+)\]', raw_hand, re.DOTALL)
        if river_match:
            cards_str = river_match.group(1)
            cards = [c.strip() for c in cards_str.split(',') if c.strip()]
            if len(cards) >= 5:
                formatted['river_card'] = self._format_card_for_display(cards[4])
            
            # Parse river action
            if '** Summary **' in raw_hand:
                river_section = raw_hand.split('** Dealing River **')[1].split('** Summary **')[0]
            else:
                river_section = raw_hand.split('** Dealing River **')[1] if '** Dealing River **' in raw_hand else ''
            
            for line in river_section.split('\n'):
                line = line.strip()
                if line and ('raises' in line.lower() or 'calls' in line.lower() or 'folds' in line.lower() or 'checks' in line.lower() or 'bets' in line.lower() or 'all-in' in line.lower()):
                    formatted['river_action'].append(line)
        
        # Parse player hands from summary
        if '** Summary **' in raw_hand:
            summary_section = raw_hand.split('** Summary **')[1]
            
            # Extract player hands
            hand_pattern = r'([^:]+):\s+showed\s+\[([^\]]+)\]\s+and\s+(won|lost|tied).*?\(([^)]+)\)'
            for match in re.finditer(hand_pattern, summary_section):
                player_name = match.group(1).strip()
                cards_str = match.group(2)
                result = match.group(3)
                hand_desc = match.group(4)
                
                cards = [self._format_card_for_display(c.strip()) for c in cards_str.split(',') if c.strip()]
                formatted['player_hands'].append({
                    'player': player_name,
                    'cards': cards,
                    'hand_description': hand_desc,
                    'result': result
                })
            
            # Extract summary lines
            for line in summary_section.split('\n'):
                line = line.strip()
                if line and ('won' in line.lower() or 'lost' in line.lower() or 'pot' in line.lower() or 'rake' in line.lower()):
                    formatted['summary'].append(line)
        
        return formatted
    
    def _format_card_for_display(self, card_str):
        """Format card string for HTML display with suit symbols"""
        if not card_str or len(card_str) < 2:
            return card_str
        
        rank = card_str[0].upper()
        suit = card_str[1].upper() if len(card_str) > 1 else ''
        
        suit_symbols = {
            'S': '♠',
            'H': '♥',
            'D': '♦',
            'C': '♣'
        }
        
        suit_colors = {
            'S': 'black',
            'C': 'black',
            'H': 'red',
            'D': 'red'
        }
        
        if suit in suit_symbols:
            color = suit_colors.get(suit, 'black')
            return f'<span style="color: {color};">{rank}{suit_symbols[suit]}</span>'
        
        return card_str

    def calculate_leak_detection(self, dataframe):
        """Detect common poker leaks"""
        leaks = []
        
        # Leak 1: Over-folding to 3-bets
        three_bet_hands = dataframe[dataframe['three_bet'] == True]
        if len(three_bet_hands) > 0:
            fold_to_3bet = dataframe[(dataframe['three_bet'] == True) & (dataframe['fold'] == True)]
            fold_rate = len(fold_to_3bet) / len(three_bet_hands) * 100
            if fold_rate > 85:  # Optimal is around 60-70%
                leaks.append({
                    'type': 'Preflop',
                    'title': 'Over-folding to 3-bets',
                    'severity': 'high' if fold_rate > 90 else 'medium',
                    'description': f'You are folding {fold_rate:.1f}% of the time when facing a 3-bet. This is too high.',
                    'suggestion': 'Consider calling or 4-betting more often, especially in position and with suited connectors or pocket pairs.',
                    'impact': (fold_rate - 70) * 0.5,  # Rough estimate
                    'hands': len(three_bet_hands),
                    'bb_per_100': -abs((fold_rate - 70) * 0.3),
                    'actual_freq': round(fold_rate, 1),
                    'optimal_freq': 65.0
                })
        
        # Leak 2: Under-3-betting
        rfi_hands = dataframe[dataframe['rfi'] == True]
        if len(rfi_hands) > 10:
            three_bet_rate = len(three_bet_hands) / len(rfi_hands) * 100
            if three_bet_rate < 5:  # Optimal is around 8-12%
                leaks.append({
                    'type': 'Preflop',
                    'title': 'Under-3-betting',
                    'severity': 'medium',
                    'description': f'Your 3-bet frequency is {three_bet_rate:.1f}% when facing a raise. This is too low.',
                    'suggestion': 'Increase your 3-betting frequency to 8-12% with value hands (pairs, suited aces, broadways) and bluffs (suited connectors, suited aces).',
                    'impact': (8 - three_bet_rate) * 0.4,
                    'hands': len(rfi_hands),
                    'bb_per_100': -abs((8 - three_bet_rate) * 0.2),
                    'actual_freq': round(three_bet_rate, 1),
                    'optimal_freq': 10.0
                })
        
        # Leak 3: Calling too much preflop
        total_hands = len(dataframe)
        if total_hands > 0:
            call_rfi_rate = len(dataframe[dataframe['call_rfi'] == True]) / total_hands * 100
            if call_rfi_rate > 15:  # Optimal is around 8-12%
                leaks.append({
                    'type': 'Preflop',
                    'title': 'Over-calling preflop',
                    'severity': 'medium',
                    'description': f'You are calling raises {call_rfi_rate:.1f}% of the time. This is too high.',
                    'suggestion': 'Tighten your calling range. Consider 3-betting or folding more often instead of calling.',
                    'impact': (call_rfi_rate - 12) * 0.3,
                    'hands': total_hands,
                    'bb_per_100': -abs((call_rfi_rate - 12) * 0.15),
                    'actual_freq': round(call_rfi_rate, 1),
                    'optimal_freq': 10.0
                })
        
        # Leak 4: Not continuation betting enough on flop
        # This would require more detailed action tracking, skipping for now
        
        # Leak 5: VPIP too high from early positions
        early_positions = ['UTG', 'MP']
        for pos in early_positions:
            pos_hands = dataframe[dataframe['position'] == pos]
            if len(pos_hands) > 5:
                vpip_rate = len(pos_hands[pos_hands['vpip'] == True]) / len(pos_hands) * 100
                optimal_vpip = 15 if pos == 'UTG' else 18
                if vpip_rate > optimal_vpip + 5:
                    leaks.append({
                        'type': 'Preflop',
                        'title': f'VPIP too high from {pos}',
                        'severity': 'medium',
                        'description': f'Your VPIP from {pos} is {vpip_rate:.1f}%. Optimal is around {optimal_vpip}%.',
                        'suggestion': f'Tighten your {pos} range. Only play premium hands and strong suited connectors.',
                        'impact': (vpip_rate - optimal_vpip) * 0.2,
                        'hands': len(pos_hands),
                        'bb_per_100': -abs((vpip_rate - optimal_vpip) * 0.1),
                        'actual_freq': round(vpip_rate, 1),
                        'optimal_freq': float(optimal_vpip)
                    })
        
        # Sort leaks by impact
        leaks.sort(key=lambda x: x.get('impact', 0), reverse=True)
        
        return leaks

    def advanced_processing(self, dataframe):
        results = {}

        df_six_players = dataframe[dataframe['no_players'] == 6]

        number_of_hands = len(dataframe)
        if number_of_hands == 0:
            # Return empty results if no hands
            return pd.DataFrame([{}])
        
        # Debug: Check hand_result column
        if 'hand_result' not in dataframe.columns:
            print("WARNING: hand_result column missing from dataframe!")
            earnings = 0.0
            BB_earnings = 0.0
        else:
            # Check for NaN values and replace with 0
            dataframe['hand_result'] = dataframe['hand_result'].fillna(0.0)
            earnings = dataframe['hand_result'].sum()
            
            # Debug output
            non_zero_results = (dataframe['hand_result'] != 0).sum()
            if non_zero_results == 0:
                print(f"WARNING: All {number_of_hands} hands have hand_result = 0.0")
                print(f"Sample hand_result values: {dataframe['hand_result'].head(10).tolist()}")
            
            # Calculate BB earnings (handle division by zero)
            # Check bb_stake column
            if 'bb_stake' not in dataframe.columns:
                print("WARNING: bb_stake column missing from dataframe!")
                bb_stakes = pd.Series([0.25] * len(dataframe))  # Default to 0.25 if missing
            else:
                bb_stakes = dataframe['bb_stake'].fillna(0.25)  # Default to 0.25 if NaN
                # Replace 0 with default to avoid division by zero
                bb_stakes = bb_stakes.replace(0.0, 0.25)
            
            # Debug: Check bb_stake values
            zero_bb_stakes = (bb_stakes == 0).sum()
            if zero_bb_stakes > 0:
                print(f"WARNING: {zero_bb_stakes} hands have bb_stake = 0, using default 0.25")
            
            dataframe['BB_earnings'] = dataframe['hand_result'] / bb_stakes
            BB_earnings = dataframe['BB_earnings'].sum()
            
            # Debug output for BB earnings
            if BB_earnings == 0.0 and earnings != 0.0:
                print(f"WARNING: BB_earnings is 0.0 but earnings is {earnings}")
                print(f"Sample bb_stake values: {bb_stakes.head(10).tolist()}")
                print(f"Sample hand_result values: {dataframe['hand_result'].head(10).tolist()}")
                print(f"Sample BB_earnings values: {dataframe['BB_earnings'].head(10).tolist()}")
        
        BB_earnings_per_100_hands = BB_earnings * 100 / number_of_hands if number_of_hands > 0 else 0
        # IMPORTANT: Always calculate VPIP on the FULL dataset, not filtered by flop/turn/river
        # VPIP is a preflop metric and should include all hands, not just those that saw postflop streets
        vpip = self.calculate_vpip(dataframe)
        vpip_rfi = self.calculate_rfi_vpip_metrics(dataframe)

        # Include HJ (5-handed) and gracefully handle any unexpected positions
        default_positions = ['UTG', 'HJ', 'MP', 'CO', 'BTN', 'SB', 'BB']
        positional_profitability = {pos: 0 for pos in default_positions}

        # Ensure any positions present in the data exist in the accumulator
        for pos in dataframe['position'].dropna().unique():
            positional_profitability.setdefault(pos, 0)

        for _, row in dataframe.iterrows():
            position = row.get('position')
            if pd.isna(position):
                continue
            if position not in positional_profitability:
                positional_profitability[position] = 0
            positional_profitability[position] += row['hand_result'] / row['bb_stake']

        rounded_positional_profitability = {pos: round(profit, 2) for pos, profit in positional_profitability.items()}

        # Calculate IP and OP profitability post-flop
        ip_profitability, op_profitability = self.calculate_ip_op_profitability(dataframe)

        # Calculate in position percentage
        in_position_percentage, out_position_percentage = self.calculate_in_position_percentage(dataframe)

        # Calculate bet rates for flop, turn, and river
        streets = ['flop', 'turn', 'river']
        for street in streets:
            bet_rates = self.calculate_bet_rates(dataframe, street)
            results.update(bet_rates)

        # Calculate total hands that reached each street (for Action Frequency metrics)
        def count_street_hands(df, street_name):
            """Count hands that reached a specific street"""
            street_mask = pd.Series([False] * len(df), index=df.index)
            
            # Method 1: Check main flop column
            if street_name == 'flop' and 'flop' in df.columns:
                street_mask = street_mask | (df['flop'] == True)
            
            # Method 2: Check if street cards exist
            if street_name == 'turn' and 'turn_cards' in df.columns:
                street_mask = street_mask | ((df['turn_cards'] != 0) & (df['turn_cards'].notna()))
            elif street_name == 'river' and 'river_cards' in df.columns:
                street_mask = street_mask | ((df['river_cards'] != 0) & (df['river_cards'].notna()))
            
            # Method 3: Check HU columns
            if street_name == 'turn' and 'turn_HU_with_hero' in df.columns:
                street_mask = street_mask | (df['turn_HU_with_hero'] == True)
            elif street_name == 'river' and 'river_HU_with_hero' in df.columns:
                street_mask = street_mask | (df['river_HU_with_hero'] == True)
            
            # Method 4: Check Raw Hand for street markers (most reliable)
            def has_street_in_raw_hand(raw_hand, street):
                if not raw_hand or not isinstance(raw_hand, str):
                    return False
                if street == 'flop':
                    return '** Dealing Flop **' in raw_hand
                elif street == 'turn':
                    return '** Dealing Turn **' in raw_hand
                elif street == 'river':
                    return '** Dealing River **' in raw_hand
                return False
            
            if 'Raw Hand' in df.columns:
                # For turn/river, only count hands where Hero reached that street
                if street_name in ['turn', 'river']:
                    def hero_reached_street(raw_hand):
                        if not raw_hand or not isinstance(raw_hand, str):
                            return False
                        if '** Dealing Flop **' not in raw_hand:
                            return False
                        if street_name == 'turn' and '** Dealing Turn **' not in raw_hand:
                            return False
                        if street_name == 'river' and '** Dealing River **' not in raw_hand:
                            return False

                        # Preflop: Hero must not fold before flop
                        if '** Dealing down cards **' in raw_hand:
                            preflop = raw_hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0]
                            if 'Hero folds' in preflop:
                                return False

                        # Flop: Hero must not fold before turn/river
                        flop_section = raw_hand.split('** Dealing Flop **')[1]
                        if '** Dealing Turn **' in flop_section:
                            flop_section = flop_section.split('** Dealing Turn **')[0]
                        elif '** Summary **' in flop_section:
                            flop_section = flop_section.split('** Summary **')[0]
                        if 'Hero folds' in flop_section:
                            return False

                        if street_name == 'river':
                            # Turn: Hero must not fold before river
                            turn_section = raw_hand.split('** Dealing Turn **')[1]
                            if '** Dealing River **' in turn_section:
                                turn_section = turn_section.split('** Dealing River **')[0]
                            elif '** Summary **' in turn_section:
                                turn_section = turn_section.split('** Summary **')[0]
                            if 'Hero folds' in turn_section:
                                return False

                        return True

                    street_mask = street_mask | df['Raw Hand'].apply(hero_reached_street)
                else:
                    street_mask = street_mask | df['Raw Hand'].apply(lambda x: has_street_in_raw_hand(x, street_name))
            
            return street_mask.sum()
        
        # Calculate detailed flop action frequency with IP/OOP/Multiway breakdown
        def calculate_flop_action_frequency(df):
            """Calculate flop action frequency broken down by IP/OOP/Multiway"""
            stats = {
                'total_hands': 0,
                'ip': {
                    'total': 0,
                    'checks': 0,
                    'bets': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0
                },
                'oop': {
                    'total': 0,
                    'checks': 0,
                    'bets': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0
                },
                'multiway': {
                    'total': 0,
                    'checks': 0,
                    'bets': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0
                }
            }
            
            try:
                # Filter to hands that reached flop AND Hero is still active
                if len(df) == 0:
                    return stats
                    
                flop_mask = pd.Series([False] * len(df), index=df.index)
                if 'flop' in df.columns:
                    flop_mask = flop_mask | (df['flop'] == True)
                if 'Raw Hand' in df.columns:
                    flop_mask = flop_mask | df['Raw Hand'].apply(lambda x: '** Dealing Flop **' in str(x) if x else False)
                
                # CRITICAL: Only count hands where Hero is active on flop (didn't fold preflop)
                if 'hero_is_active_on_flop' in df.columns:
                    flop_mask = flop_mask & (df['hero_is_active_on_flop'] == True)
                elif 'hero_saw_flop' in df.columns:
                    flop_mask = flop_mask & (df['hero_saw_flop'] == True)
                # Also verify from Raw Hand that Hero didn't fold preflop
                if 'Raw Hand' in df.columns:
                    def hero_active_on_flop(raw_hand):
                        """Check if Hero is active on flop (didn't fold preflop)"""
                        if not raw_hand or not isinstance(raw_hand, str):
                            return False
                        if '** Dealing Flop **' not in raw_hand:
                            return False
                        # Check if Hero folded before flop
                        if '** Dealing down cards **' in raw_hand and '** Dealing Flop **' in raw_hand:
                            preflop = raw_hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0]
                            # Look for Hero's actions in preflop
                            hero_lines = [l.strip() for l in preflop.split('\n') if 'Hero' in l and l.strip()]
                            for line in hero_lines:
                                if 'folds' in line.lower() and 'Hero' in line:
                                    return False  # Hero folded preflop
                        return True  # Hero didn't fold preflop (or no fold found)
                    
                    hero_active_mask = df['Raw Hand'].apply(hero_active_on_flop)
                    flop_mask = flop_mask & hero_active_mask
                
                flop_df = df[flop_mask].copy()
                if len(flop_df) == 0:
                    return stats
            except Exception as e:
                print(f"Error filtering flop hands: {e}")
                import traceback
                traceback.print_exc()
                return stats
            
            try:
                for _, row in flop_df.iterrows():
                    try:
                        # Determine if multiway (3+ players active on flop)
                        is_multiway = False
                        try:
                            if 'players_active_on_flop' in flop_df.columns and pd.notna(row.get('players_active_on_flop', None)):
                                players_list = row['players_active_on_flop']
                                if isinstance(players_list, list):
                                    is_multiway = len(players_list) >= 3
                                elif isinstance(players_list, (str, bytes)) and players_list:
                                    # Try to parse if it's a string representation
                                    try:
                                        import ast
                                        parsed = ast.literal_eval(str(players_list))
                                        if isinstance(parsed, list):
                                            is_multiway = len(parsed) >= 3
                                    except:
                                        pass
                            elif 'flop_HU_with_hero' in flop_df.columns and pd.notna(row.get('flop_HU_with_hero', None)):
                                is_multiway = not bool(row['flop_HU_with_hero'])
                            # Also check by counting players who saw flop
                            elif 'players_see_flop' in flop_df.columns and pd.notna(row.get('players_see_flop', None)):
                                is_multiway = int(row['players_see_flop']) >= 3
                        except Exception:
                            pass

                        # Fallback: derive multiway from raw hand by counting players remaining at flop
                        if not is_multiway and 'Raw Hand' in flop_df.columns and pd.notna(row.get('Raw Hand', None)):
                            raw_hand = str(row.get('Raw Hand', ''))
                            if '** Dealing Flop **' in raw_hand:
                                # Get all seated players
                                players = []
                                for line in raw_hand.split('\n'):
                                    line = line.strip()
                                    if line.startswith('Seat ') and ':' in line:
                                        try:
                                            name = line.split(':', 1)[1].strip().split(' ')[0]
                                            if name:
                                                players.append(name)
                                        except Exception:
                                            continue

                                active_players = set(players)

                                # Remove preflop folders
                                if '** Dealing down cards **' in raw_hand:
                                    preflop = raw_hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0]
                                    for line in preflop.split('\n'):
                                        if 'folds' in line:
                                            player = line.strip().split(' ')[0]
                                            if player:
                                                active_players.discard(player)

                                is_multiway = len(active_players) >= 3
                        
                        # Determine IP/OOP
                        is_ip = False
                        try:
                            if 'flop_Position' in flop_df.columns and pd.notna(row.get('flop_Position', None)):
                                # flop_Position is True when Hero is in position
                                is_ip = bool(row['flop_Position'])
                            elif 'hero_position_vs_preflop_raiser_flop' in flop_df.columns and pd.notna(row.get('hero_position_vs_preflop_raiser_flop', None)):
                                pos = row['hero_position_vs_preflop_raiser_flop']
                                if isinstance(pos, str):
                                    is_ip = (pos == 'IP')
                            elif 'hero_relative_position_category_flop' in flop_df.columns and pd.notna(row.get('hero_relative_position_category_flop', None)):
                                pos_cat = row['hero_relative_position_category_flop']
                                if isinstance(pos_cat, str):
                                    is_ip = (pos_cat == 'last_to_act')
                        except Exception:
                            pass
                        
                        # Get Hero's first action on flop
                        hero_first_action = None
                        try:
                            if 'flop_OP' in flop_df.columns and pd.notna(row.get('flop_OP', None)):
                                flop_op = row['flop_OP']
                                if isinstance(flop_op, list) and len(flop_op) > 0:
                                    if isinstance(flop_op[0], list) and len(flop_op[0]) > 0:
                                        hero_first_action = str(flop_op[0][0]).lower()
                                elif isinstance(flop_op, (str, bytes)) and flop_op:
                                    try:
                                        import ast
                                        parsed = ast.literal_eval(str(flop_op))
                                        if isinstance(parsed, list) and len(parsed) > 0:
                                            if isinstance(parsed[0], list) and len(parsed[0]) > 0:
                                                hero_first_action = str(parsed[0][0]).lower()
                                    except:
                                        pass
                            
                            if not hero_first_action and 'flop_IP' in flop_df.columns and pd.notna(row.get('flop_IP', None)):
                                flop_ip = row['flop_IP']
                                if isinstance(flop_ip, list) and len(flop_ip) > 0:
                                    if isinstance(flop_ip[0], list) and len(flop_ip[0]) > 0:
                                        hero_first_action = str(flop_ip[0][0]).lower()
                                elif isinstance(flop_ip, (str, bytes)) and flop_ip:
                                    try:
                                        import ast
                                        parsed = ast.literal_eval(str(flop_ip))
                                        if isinstance(parsed, list) and len(parsed) > 0:
                                            if isinstance(parsed[0], list) and len(parsed[0]) > 0:
                                                hero_first_action = str(parsed[0][0]).lower()
                                    except:
                                        pass
                        except Exception:
                            pass
                        
                        # Also try to get from raw hand if available
                        if not hero_first_action and 'Raw Hand' in flop_df.columns and pd.notna(row.get('Raw Hand', None)):
                            raw_hand = str(row['Raw Hand'])
                            if '** Dealing Flop **' in raw_hand:
                                flop_section = raw_hand.split('** Dealing Flop **')[1]
                                if '** Dealing Turn **' in flop_section:
                                    flop_section = flop_section.split('** Dealing Turn **')[0]
                                elif '** Summary **' in flop_section:
                                    flop_section = flop_section.split('** Summary **')[0]
                                
                                # Look for Hero's first action
                                for line in flop_section.split('\n'):
                                    line = line.strip()
                                    if 'Hero' in line:
                                        if 'checks' in line.lower():
                                            hero_first_action = 'checks'
                                        elif 'bets' in line.lower():
                                            hero_first_action = 'bets'
                                        elif 'calls' in line.lower():
                                            hero_first_action = 'calls'
                                        elif 'folds' in line.lower():
                                            hero_first_action = 'folds'
                                        elif 'raises' in line.lower():
                                            hero_first_action = 'raises'
                                        break
                        
                        # Categorize and count
                        if is_multiway:
                            stats['multiway']['total'] += 1
                            if hero_first_action:
                                if 'check' in hero_first_action.lower():
                                    stats['multiway']['checks'] += 1
                                elif 'bet' in hero_first_action.lower():
                                    stats['multiway']['bets'] += 1
                                elif 'call' in hero_first_action.lower():
                                    stats['multiway']['calls'] += 1
                                elif 'fold' in hero_first_action.lower():
                                    stats['multiway']['folds'] += 1
                                elif 'raise' in hero_first_action.lower():
                                    stats['multiway']['raises'] += 1
                        elif is_ip:
                            stats['ip']['total'] += 1
                            if hero_first_action:
                                if 'check' in hero_first_action.lower():
                                    stats['ip']['checks'] += 1
                                elif 'bet' in hero_first_action.lower():
                                    stats['ip']['bets'] += 1
                                elif 'call' in hero_first_action.lower():
                                    stats['ip']['calls'] += 1
                                elif 'fold' in hero_first_action.lower():
                                    stats['ip']['folds'] += 1
                                elif 'raise' in hero_first_action.lower():
                                    stats['ip']['raises'] += 1
                        else:
                            stats['oop']['total'] += 1
                            if hero_first_action:
                                if 'check' in hero_first_action.lower():
                                    stats['oop']['checks'] += 1
                                elif 'bet' in hero_first_action.lower():
                                    stats['oop']['bets'] += 1
                                elif 'call' in hero_first_action.lower():
                                    stats['oop']['calls'] += 1
                                elif 'fold' in hero_first_action.lower():
                                    stats['oop']['folds'] += 1
                                elif 'raise' in hero_first_action.lower():
                                    stats['oop']['raises'] += 1
                    except Exception:
                        # Skip row-level failures but keep overall processing
                        continue
            except Exception as e:
                print(f"Error processing flop action rows: {e}")
                import traceback
                traceback.print_exc()
            
            # Ensure total_hands matches the categorized totals
            stats['total_hands'] = stats['ip']['total'] + stats['oop']['total'] + stats['multiway']['total']
            
            return stats

        def calculate_turn_action_frequency(df):
            """Calculate turn action frequency broken down by IP/OOP"""
            stats = {
                'total_hands': 0,
                'bets': 0,
                'checks': 0,
                'calls': 0,
                'folds': 0,
                'raises': 0,
                'bet_pct': 0,
                'check_pct': 0,
                'ip': {
                    'total_hands': 0,
                    'bets': 0,
                    'checks': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0,
                    'bet_pct': 0,
                    'check_pct': 0,
                    'uncounted': 0
                },
                'oop': {
                    'total_hands': 0,
                    'bets': 0,
                    'checks': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0,
                    'bet_pct': 0,
                    'check_pct': 0,
                    'uncounted': 0
                },
                'multiway': {
                    'total_hands': 0,
                    'bets': 0,
                    'checks': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0,
                    'bet_pct': 0,
                    'check_pct': 0,
                    'uncounted': 0
                },
                'unknown': {
                    'total_hands': 0
                }
            }

            if len(df) == 0:
                return stats

            # Filter to hands where Hero reached the turn
            turn_mask = pd.Series([False] * len(df), index=df.index)
            if 'hero_is_active_on_turn' in df.columns:
                turn_mask = turn_mask | (df['hero_is_active_on_turn'] == True)
            elif 'hero_saw_turn' in df.columns:
                turn_mask = turn_mask | (df['hero_saw_turn'] == True)

            if 'Raw Hand' in df.columns and not turn_mask.any():
                def hero_reached_turn(raw_hand):
                    if not raw_hand or not isinstance(raw_hand, str):
                        return False
                    if '** Dealing Flop **' not in raw_hand or '** Dealing Turn **' not in raw_hand:
                        return False
                    if '** Dealing down cards **' in raw_hand:
                        preflop = raw_hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0]
                        if 'Hero folds' in preflop:
                            return False
                    flop_section = raw_hand.split('** Dealing Flop **')[1]
                    if '** Dealing Turn **' in flop_section:
                        flop_section = flop_section.split('** Dealing Turn **')[0]
                    elif '** Summary **' in flop_section:
                        flop_section = flop_section.split('** Summary **')[0]
                    if 'Hero folds' in flop_section:
                        return False
                    return True

                turn_mask = df['Raw Hand'].apply(hero_reached_turn)

            turn_df = df[turn_mask].copy()
            if len(turn_df) == 0:
                return stats

            for _, row in turn_df.iterrows():
                # Determine if multiway (3+ players active on turn)
                is_multiway = False
                try:
                    if 'players_active_on_turn' in turn_df.columns and pd.notna(row.get('players_active_on_turn', None)):
                        players_list = row['players_active_on_turn']
                        if isinstance(players_list, list):
                            is_multiway = len(players_list) >= 3
                        elif isinstance(players_list, (str, bytes)) and players_list:
                            try:
                                import ast
                                parsed = ast.literal_eval(str(players_list))
                                if isinstance(parsed, list):
                                    is_multiway = len(parsed) >= 3
                            except Exception:
                                pass
                    elif 'turn_HU_with_hero' in turn_df.columns and pd.notna(row.get('turn_HU_with_hero', None)):
                        is_multiway = not bool(row.get('turn_HU_with_hero'))
                    elif 'players_see_turn' in turn_df.columns and pd.notna(row.get('players_see_turn', None)):
                        is_multiway = int(row.get('players_see_turn', 0)) >= 3
                except Exception:
                    pass

                # Fallback: derive multiway from raw hand by counting players remaining at turn
                if not is_multiway and 'Raw Hand' in turn_df.columns and pd.notna(row.get('Raw Hand', None)):
                    raw_hand = str(row.get('Raw Hand', ''))
                    if '** Dealing Flop **' in raw_hand and '** Dealing Turn **' in raw_hand:
                        # Get all seated players
                        players = []
                        for line in raw_hand.split('\n'):
                            line = line.strip()
                            if line.startswith('Seat ') and ':' in line:
                                try:
                                    name = line.split(':', 1)[1].strip().split(' ')[0]
                                    if name:
                                        players.append(name)
                                except Exception:
                                    continue

                        active_players = set(players)

                        # Remove preflop folders
                        if '** Dealing down cards **' in raw_hand:
                            preflop = raw_hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0]
                            for line in preflop.split('\n'):
                                if 'folds' in line:
                                    player = line.strip().split(' ')[0]
                                    if player:
                                        active_players.discard(player)

                        # Remove flop folders
                        flop_section = raw_hand.split('** Dealing Flop **')[1]
                        if '** Dealing Turn **' in flop_section:
                            flop_section = flop_section.split('** Dealing Turn **')[0]
                        elif '** Summary **' in flop_section:
                            flop_section = flop_section.split('** Summary **')[0]
                        for line in flop_section.split('\n'):
                            if 'folds' in line:
                                player = line.strip().split(' ')[0]
                                if player:
                                    active_players.discard(player)

                        is_multiway = len(active_players) >= 3

                # Determine IP/OOP on turn
                is_ip = None
                try:
                    if 'hero_position_vs_preflop_raiser_turn' in turn_df.columns and pd.notna(row.get('hero_position_vs_preflop_raiser_turn', None)):
                        pos = row['hero_position_vs_preflop_raiser_turn']
                        if isinstance(pos, str):
                            if pos == 'IP':
                                is_ip = True
                            elif pos == 'OOP':
                                is_ip = False
                    elif 'hero_relative_position_category_turn' in turn_df.columns and pd.notna(row.get('hero_relative_position_category_turn', None)):
                        pos_cat = row['hero_relative_position_category_turn']
                        if isinstance(pos_cat, str):
                            if pos_cat == 'last_to_act':
                                is_ip = True
                            elif pos_cat == 'first_to_act':
                                is_ip = False
                    elif 'flop_Position' in turn_df.columns and pd.notna(row.get('flop_Position', None)):
                        # In HU pots, position stays the same across streets
                        is_ip = bool(row.get('flop_Position'))
                except Exception:
                    is_ip = None

                # Get Hero's first action on turn
                hero_first_action = None
                try:
                    def extract_first_action(action_list):
                        if isinstance(action_list, list) and len(action_list) > 0:
                            if isinstance(action_list[0], list) and len(action_list[0]) > 0:
                                return str(action_list[0][0]).lower()
                        elif isinstance(action_list, (str, bytes)) and action_list:
                            try:
                                import ast
                                parsed = ast.literal_eval(str(action_list))
                                if isinstance(parsed, list) and len(parsed) > 0:
                                    if isinstance(parsed[0], list) and len(parsed[0]) > 0:
                                        return str(parsed[0][0]).lower()
                            except Exception:
                                return None
                        return None

                    # Prefer the list that matches Hero's position
                    if is_ip is True and 'turn_IP' in turn_df.columns and pd.notna(row.get('turn_IP', None)):
                        hero_first_action = extract_first_action(row.get('turn_IP'))
                    elif is_ip is False and 'turn_OP' in turn_df.columns and pd.notna(row.get('turn_OP', None)):
                        hero_first_action = extract_first_action(row.get('turn_OP'))

                    if not hero_first_action:
                        if 'turn_OP' in turn_df.columns and pd.notna(row.get('turn_OP', None)):
                            hero_first_action = extract_first_action(row.get('turn_OP'))
                    if not hero_first_action:
                        if 'turn_IP' in turn_df.columns and pd.notna(row.get('turn_IP', None)):
                            hero_first_action = extract_first_action(row.get('turn_IP'))
                except Exception:
                    pass

                if not hero_first_action and 'Raw Hand' in turn_df.columns and pd.notna(row.get('Raw Hand', None)):
                    raw_hand = str(row['Raw Hand'])
                    if '** Dealing Turn **' in raw_hand:
                        turn_section = raw_hand.split('** Dealing Turn **')[1]
                        if '** Dealing River **' in turn_section:
                            turn_section = turn_section.split('** Dealing River **')[0]
                        elif '** Summary **' in turn_section:
                            turn_section = turn_section.split('** Summary **')[0]
                        for line in turn_section.split('\n'):
                            line = line.strip()
                            if 'Hero' in line:
                                if 'checks' in line.lower():
                                    hero_first_action = 'checks'
                                elif 'bets' in line.lower():
                                    hero_first_action = 'bets'
                                elif 'calls' in line.lower():
                                    hero_first_action = 'calls'
                                elif 'folds' in line.lower():
                                    hero_first_action = 'folds'
                                elif 'raises' in line.lower():
                                    hero_first_action = 'raises'
                                break

                if is_multiway:
                    target = stats['multiway']
                else:
                    target = stats['ip'] if is_ip is True else stats['oop'] if is_ip is False else None
                    if target is None:
                        stats['unknown']['total_hands'] += 1
                        continue

                target['total_hands'] += 1
                if hero_first_action:
                    if 'check' in hero_first_action:
                        target['checks'] += 1
                    elif 'bet' in hero_first_action:
                        target['bets'] += 1
                    elif 'call' in hero_first_action:
                        target['calls'] += 1
                    elif 'fold' in hero_first_action:
                        target['folds'] += 1
                    elif 'raise' in hero_first_action:
                        target['raises'] += 1
                else:
                    target['uncounted'] += 1

            # Roll up totals
            stats['total_hands'] = stats['ip']['total_hands'] + stats['oop']['total_hands'] + stats['multiway']['total_hands']
            stats['bets'] = stats['ip']['bets'] + stats['oop']['bets'] + stats['multiway']['bets']
            stats['checks'] = stats['ip']['checks'] + stats['oop']['checks'] + stats['multiway']['checks']
            stats['calls'] = stats['ip']['calls'] + stats['oop']['calls'] + stats['multiway']['calls']
            stats['folds'] = stats['ip']['folds'] + stats['oop']['folds'] + stats['multiway']['folds']
            stats['raises'] = stats['ip']['raises'] + stats['oop']['raises'] + stats['multiway']['raises']

            if stats['total_hands'] > 0:
                stats['bet_pct'] = round((stats['bets'] / stats['total_hands']) * 100, 1)
                stats['check_pct'] = round((stats['checks'] / stats['total_hands']) * 100, 1)

            for key in ['ip', 'oop']:
                total = stats[key]['total_hands']
                if total > 0:
                    stats[key]['bet_pct'] = round((stats[key]['bets'] / total) * 100, 1)
                    stats[key]['check_pct'] = round((stats[key]['checks'] / total) * 100, 1)
            total_multiway = stats['multiway']['total_hands']
            if total_multiway > 0:
                stats['multiway']['bet_pct'] = round((stats['multiway']['bets'] / total_multiway) * 100, 1)
                stats['multiway']['check_pct'] = round((stats['multiway']['checks'] / total_multiway) * 100, 1)

            return stats

        def calculate_river_action_frequency(df):
            """Calculate river action frequency broken down by IP/OOP"""
            stats = {
                'total_hands': 0,
                'bets': 0,
                'checks': 0,
                'calls': 0,
                'folds': 0,
                'raises': 0,
                'bet_pct': 0,
                'check_pct': 0,
                'ip': {
                    'total_hands': 0,
                    'bets': 0,
                    'checks': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0,
                    'bet_pct': 0,
                    'check_pct': 0,
                    'uncounted': 0
                },
                'oop': {
                    'total_hands': 0,
                    'bets': 0,
                    'checks': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0,
                    'bet_pct': 0,
                    'check_pct': 0,
                    'uncounted': 0
                },
                'multiway': {
                    'total_hands': 0,
                    'bets': 0,
                    'checks': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0,
                    'bet_pct': 0,
                    'check_pct': 0,
                    'uncounted': 0
                },
                'unknown': {
                    'total_hands': 0
                }
            }

            if len(df) == 0:
                return stats

            river_mask = pd.Series([False] * len(df), index=df.index)
            if 'hero_is_active_on_river' in df.columns:
                river_mask = river_mask | (df['hero_is_active_on_river'] == True)
            elif 'hero_saw_river' in df.columns:
                river_mask = river_mask | (df['hero_saw_river'] == True)

            if 'Raw Hand' in df.columns and not river_mask.any():
                def hero_reached_river(raw_hand):
                    if not raw_hand or not isinstance(raw_hand, str):
                        return False
                    if '** Dealing Flop **' not in raw_hand or '** Dealing River **' not in raw_hand:
                        return False
                    if '** Dealing down cards **' in raw_hand:
                        preflop = raw_hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0]
                        if 'Hero folds' in preflop:
                            return False
                    flop_section = raw_hand.split('** Dealing Flop **')[1]
                    if '** Dealing Turn **' in flop_section:
                        flop_section = flop_section.split('** Dealing Turn **')[0]
                    elif '** Summary **' in flop_section:
                        flop_section = flop_section.split('** Summary **')[0]
                    if 'Hero folds' in flop_section:
                        return False
                    turn_section = raw_hand.split('** Dealing Turn **')[1]
                    if '** Dealing River **' in turn_section:
                        turn_section = turn_section.split('** Dealing River **')[0]
                    elif '** Summary **' in turn_section:
                        turn_section = turn_section.split('** Summary **')[0]
                    if 'Hero folds' in turn_section:
                        return False
                    return True

                river_mask = df['Raw Hand'].apply(hero_reached_river)

            river_df = df[river_mask].copy()
            if len(river_df) == 0:
                return stats

            for _, row in river_df.iterrows():
                # Determine if multiway (3+ players active on river)
                is_multiway = False
                try:
                    if 'players_active_on_river' in river_df.columns and pd.notna(row.get('players_active_on_river', None)):
                        players_list = row['players_active_on_river']
                        if isinstance(players_list, list):
                            is_multiway = len(players_list) >= 3
                        elif isinstance(players_list, (str, bytes)) and players_list:
                            try:
                                import ast
                                parsed = ast.literal_eval(str(players_list))
                                if isinstance(parsed, list):
                                    is_multiway = len(parsed) >= 3
                            except Exception:
                                pass
                    elif 'river_HU_with_hero' in river_df.columns and pd.notna(row.get('river_HU_with_hero', None)):
                        is_multiway = not bool(row.get('river_HU_with_hero'))
                    elif 'players_see_river' in river_df.columns and pd.notna(row.get('players_see_river', None)):
                        is_multiway = int(row.get('players_see_river', 0)) >= 3
                except Exception:
                    pass

                if not is_multiway and 'Raw Hand' in river_df.columns and pd.notna(row.get('Raw Hand', None)):
                    raw_hand = str(row.get('Raw Hand', ''))
                    if '** Dealing Flop **' in raw_hand and '** Dealing River **' in raw_hand:
                        players = []
                        for line in raw_hand.split('\n'):
                            line = line.strip()
                            if line.startswith('Seat ') and ':' in line:
                                try:
                                    name = line.split(':', 1)[1].strip().split(' ')[0]
                                    if name:
                                        players.append(name)
                                except Exception:
                                    continue

                        active_players = set(players)

                        if '** Dealing down cards **' in raw_hand:
                            preflop = raw_hand.split('** Dealing down cards **')[1].split('** Dealing Flop **')[0]
                            for line in preflop.split('\n'):
                                if 'folds' in line:
                                    player = line.strip().split(' ')[0]
                                    if player:
                                        active_players.discard(player)

                        flop_section = raw_hand.split('** Dealing Flop **')[1]
                        if '** Dealing Turn **' in flop_section:
                            flop_section = flop_section.split('** Dealing Turn **')[0]
                        elif '** Summary **' in flop_section:
                            flop_section = flop_section.split('** Summary **')[0]
                        for line in flop_section.split('\n'):
                            if 'folds' in line:
                                player = line.strip().split(' ')[0]
                                if player:
                                    active_players.discard(player)

                        turn_section = raw_hand.split('** Dealing Turn **')[1]
                        if '** Dealing River **' in turn_section:
                            turn_section = turn_section.split('** Dealing River **')[0]
                        elif '** Summary **' in turn_section:
                            turn_section = turn_section.split('** Summary **')[0]
                        for line in turn_section.split('\n'):
                            if 'folds' in line:
                                player = line.strip().split(' ')[0]
                                if player:
                                    active_players.discard(player)

                        is_multiway = len(active_players) >= 3

                # Determine IP/OOP on river
                is_ip = None
                try:
                    if 'hero_position_vs_preflop_raiser_river' in river_df.columns and pd.notna(row.get('hero_position_vs_preflop_raiser_river', None)):
                        pos = row['hero_position_vs_preflop_raiser_river']
                        if isinstance(pos, str):
                            if pos == 'IP':
                                is_ip = True
                            elif pos == 'OOP':
                                is_ip = False
                    elif 'hero_relative_position_category_river' in river_df.columns and pd.notna(row.get('hero_relative_position_category_river', None)):
                        pos_cat = row['hero_relative_position_category_river']
                        if isinstance(pos_cat, str):
                            if pos_cat == 'last_to_act':
                                is_ip = True
                            elif pos_cat == 'first_to_act':
                                is_ip = False
                    elif 'flop_Position' in river_df.columns and pd.notna(row.get('flop_Position', None)):
                        is_ip = bool(row.get('flop_Position'))
                except Exception:
                    is_ip = None

                # Get Hero's first action on river
                hero_first_action = None
                try:
                    def extract_first_action(action_list):
                        if isinstance(action_list, list) and len(action_list) > 0:
                            if isinstance(action_list[0], list) and len(action_list[0]) > 0:
                                return str(action_list[0][0]).lower()
                        elif isinstance(action_list, (str, bytes)) and action_list:
                            try:
                                import ast
                                parsed = ast.literal_eval(str(action_list))
                                if isinstance(parsed, list) and len(parsed) > 0:
                                    if isinstance(parsed[0], list) and len(parsed[0]) > 0:
                                        return str(parsed[0][0]).lower()
                            except Exception:
                                return None
                        return None

                    if is_ip is True and 'river_IP' in river_df.columns and pd.notna(row.get('river_IP', None)):
                        hero_first_action = extract_first_action(row.get('river_IP'))
                    elif is_ip is False and 'river_OP' in river_df.columns and pd.notna(row.get('river_OP', None)):
                        hero_first_action = extract_first_action(row.get('river_OP'))

                    if not hero_first_action:
                        if 'river_OP' in river_df.columns and pd.notna(row.get('river_OP', None)):
                            hero_first_action = extract_first_action(row.get('river_OP'))
                    if not hero_first_action:
                        if 'river_IP' in river_df.columns and pd.notna(row.get('river_IP', None)):
                            hero_first_action = extract_first_action(row.get('river_IP'))
                except Exception:
                    pass

                if not hero_first_action and 'Raw Hand' in river_df.columns and pd.notna(row.get('Raw Hand', None)):
                    raw_hand = str(row['Raw Hand'])
                    if '** Dealing River **' in raw_hand:
                        river_section = raw_hand.split('** Dealing River **')[1]
                        if '** Summary **' in river_section:
                            river_section = river_section.split('** Summary **')[0]
                        for line in river_section.split('\n'):
                            line = line.strip()
                            if 'Hero' in line:
                                if 'checks' in line.lower():
                                    hero_first_action = 'checks'
                                elif 'bets' in line.lower():
                                    hero_first_action = 'bets'
                                elif 'calls' in line.lower():
                                    hero_first_action = 'calls'
                                elif 'folds' in line.lower():
                                    hero_first_action = 'folds'
                                elif 'raises' in line.lower():
                                    hero_first_action = 'raises'
                                break

                if is_multiway:
                    target = stats['multiway']
                else:
                    target = stats['ip'] if is_ip is True else stats['oop'] if is_ip is False else None
                    if target is None:
                        stats['unknown']['total_hands'] += 1
                        continue

                target['total_hands'] += 1
                if hero_first_action:
                    if 'check' in hero_first_action:
                        target['checks'] += 1
                    elif 'bet' in hero_first_action:
                        target['bets'] += 1
                    elif 'call' in hero_first_action:
                        target['calls'] += 1
                    elif 'fold' in hero_first_action:
                        target['folds'] += 1
                    elif 'raise' in hero_first_action:
                        target['raises'] += 1
                else:
                    target['uncounted'] += 1

            # Roll up totals
            stats['total_hands'] = stats['ip']['total_hands'] + stats['oop']['total_hands'] + stats['multiway']['total_hands']
            stats['bets'] = stats['ip']['bets'] + stats['oop']['bets'] + stats['multiway']['bets']
            stats['checks'] = stats['ip']['checks'] + stats['oop']['checks'] + stats['multiway']['checks']
            stats['calls'] = stats['ip']['calls'] + stats['oop']['calls'] + stats['multiway']['calls']
            stats['folds'] = stats['ip']['folds'] + stats['oop']['folds'] + stats['multiway']['folds']
            stats['raises'] = stats['ip']['raises'] + stats['oop']['raises'] + stats['multiway']['raises']

            if stats['total_hands'] > 0:
                stats['bet_pct'] = round((stats['bets'] / stats['total_hands']) * 100, 1)
                stats['check_pct'] = round((stats['checks'] / stats['total_hands']) * 100, 1)

            for key in ['ip', 'oop', 'multiway']:
                total = stats[key]['total_hands']
                if total > 0:
                    stats[key]['bet_pct'] = round((stats[key]['bets'] / total) * 100, 1)
                    stats[key]['check_pct'] = round((stats[key]['checks'] / total) * 100, 1)

            return stats
        
        # Calculate flop action frequency
        try:
            flop_action_freq = calculate_flop_action_frequency(dataframe)
            # Ensure it always has the expected structure
            if not isinstance(flop_action_freq, dict):
                flop_action_freq = {'total_hands': 0, 'ip': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0},
                                   'oop': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0},
                                   'multiway': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0}}
            # Always prefer the sum of categorized totals to avoid inconsistencies
            derived_total = (
                int(flop_action_freq.get('ip', {}).get('total', 0)) +
                int(flop_action_freq.get('oop', {}).get('total', 0)) +
                int(flop_action_freq.get('multiway', {}).get('total', 0))
            )
            if derived_total > 0:
                flop_action_freq['total_hands'] = derived_total
            print(f"Flop Action Frequency calculated: {flop_action_freq.get('total_hands', 0)} total flops")
        except Exception as e:
            print(f"Error calculating flop action frequency: {e}")
            import traceback
            traceback.print_exc()
            flop_action_freq = {'total_hands': 0, 'ip': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0},
                               'oop': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0},
                               'multiway': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0}}

        # Calculate turn action frequency
        try:
            turn_action_freq = calculate_turn_action_frequency(dataframe)
            if not isinstance(turn_action_freq, dict):
                turn_action_freq = {
                    'total_hands': 0,
                    'bets': 0,
                    'checks': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0,
                    'bet_pct': 0,
                    'check_pct': 0,
                    'ip': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0},
                    'oop': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0}
                }
        except Exception as e:
            print(f"Error calculating turn action frequency: {e}")
            import traceback
            traceback.print_exc()
            turn_action_freq = {
                'total_hands': 0,
                'bets': 0,
                'checks': 0,
                'calls': 0,
                'folds': 0,
                'raises': 0,
                'bet_pct': 0,
                'check_pct': 0,
                'ip': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0},
                'oop': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0}
            }

        # Calculate river action frequency
        try:
            river_action_freq = calculate_river_action_frequency(dataframe)
            if not isinstance(river_action_freq, dict):
                river_action_freq = {
                    'total_hands': 0,
                    'bets': 0,
                    'checks': 0,
                    'calls': 0,
                    'folds': 0,
                    'raises': 0,
                    'bet_pct': 0,
                    'check_pct': 0,
                    'ip': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0},
                    'oop': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0},
                    'multiway': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0},
                    'unknown': {'total_hands': 0}
                }
        except Exception as e:
            print(f"Error calculating river action frequency: {e}")
            import traceback
            traceback.print_exc()
            river_action_freq = {
                'total_hands': 0,
                'bets': 0,
                'checks': 0,
                'calls': 0,
                'folds': 0,
                'raises': 0,
                'bet_pct': 0,
                'check_pct': 0,
                'ip': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0},
                'oop': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0},
                'multiway': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'bet_pct': 0, 'check_pct': 0, 'uncounted': 0},
                'unknown': {'total_hands': 0}
            }
        
        # Calculate and store Action Frequency for each street
        # For flop totals, count only hands where Hero is active on the flop
        flop_total = None
        try:
            if 'hero_is_active_on_flop' in dataframe.columns:
                flop_total = int((dataframe['hero_is_active_on_flop'] == True).sum())
            elif 'hero_saw_flop' in dataframe.columns:
                flop_total = int((dataframe['hero_saw_flop'] == True).sum())
        except Exception:
            flop_total = None

        if flop_total is None:
            flop_total = count_street_hands(dataframe, 'flop')
        # For turn totals, count only hands where Hero reached the turn via the flop
        turn_total = None
        try:
            has_turn_active = 'hero_is_active_on_turn' in dataframe.columns
            has_turn_saw = 'hero_saw_turn' in dataframe.columns
            has_flop_active = 'hero_is_active_on_flop' in dataframe.columns
            has_flop_saw = 'hero_saw_flop' in dataframe.columns

            if has_turn_active or has_turn_saw:
                if has_turn_active:
                    turn_mask = (dataframe['hero_is_active_on_turn'] == True)
                else:
                    turn_mask = (dataframe['hero_saw_turn'] == True)

                # Ensure Hero also reached the flop first
                if has_flop_active:
                    turn_mask = turn_mask & (dataframe['hero_is_active_on_flop'] == True)
                elif has_flop_saw:
                    turn_mask = turn_mask & (dataframe['hero_saw_flop'] == True)

                turn_total = int(turn_mask.sum())
        except Exception:
            turn_total = None

        if turn_total is None:
            turn_total = count_street_hands(dataframe, 'turn')
        river_total = count_street_hands(dataframe, 'river')
        
        # Ensure flop_action_freq has total_hands set correctly
        if isinstance(flop_action_freq, dict):
            if flop_action_freq.get('total_hands', 0) == 0:
                flop_action_freq['total_hands'] = int(flop_total)
        
        results['Flop Action Frequency'] = flop_action_freq
        print(f"Stored Flop Action Frequency in results: {results.get('Flop Action Frequency', {}).get('total_hands', 'NOT FOUND')}")
        if isinstance(turn_action_freq, dict) and turn_action_freq.get('total_hands', 0) == 0:
            turn_action_freq['total_hands'] = int(turn_total)
        results['Turn Action Frequency'] = turn_action_freq
        if isinstance(river_action_freq, dict) and river_action_freq.get('total_hands', 0) == 0:
            river_action_freq['total_hands'] = int(river_total)
        results['River Action Frequency'] = river_action_freq

        # Calculate high card analysis for each street
        try:
            flop_high_card = self.calculate_street_high_card_analysis(dataframe, 'flop')
        except Exception as e:
            print(f"Error calculating flop high card: {e}")
            flop_high_card = {}
        
        try:
            turn_high_card = self.calculate_street_high_card_analysis(dataframe, 'turn')
        except Exception as e:
            print(f"Error calculating turn high card: {e}")
            turn_high_card = {}
        
        try:
            river_high_card = self.calculate_street_high_card_analysis(dataframe, 'river')
        except Exception as e:
            print(f"Error calculating river high card: {e}")
            river_high_card = {}
        
        # Calculate board high card analysis
        try:
            board_high_card = self.calculate_board_high_card_analysis(dataframe)
        except Exception as e:
            print(f"Error calculating board high card: {e}")
            board_high_card = {}
        
        # Calculate hand matrix analysis
        try:
            hand_matrix = self.calculate_hand_matrix_analysis(dataframe)
            # Debug: print how many hands were found
            total_hands_in_matrix = sum(
                sum(combo_data.get('total_hands', 0) for combo_data in group.values() if isinstance(combo_data, dict))
                for group in hand_matrix.values() if isinstance(group, dict)
            )
            if total_hands_in_matrix > 0:
                print(f"Generated hand matrix with {total_hands_in_matrix} total hands")
        except Exception as e:
            print(f"Error calculating hand matrix: {e}")
            import traceback
            traceback.print_exc()
            hand_matrix = {'Pairs': {}, 'Suited': {}, 'Offsuit': {}}
        
        # Calculate leak detection
        try:
            leaks = self.calculate_leak_detection(dataframe)
        except Exception as e:
            print(f"Error calculating leaks: {e}")
            leaks = []
        
        # Calculate positional matchups for each street
        try:
            flop_positional_matchups = self.calculate_street_positional_matchups(dataframe, 'flop')
        except Exception as e:
            print(f"Error calculating flop positional matchups: {e}")
            flop_positional_matchups = {}
        
        try:
            turn_positional_matchups = self.calculate_street_positional_matchups(dataframe, 'turn')
        except Exception as e:
            print(f"Error calculating turn positional matchups: {e}")
            turn_positional_matchups = {}
        
        try:
            river_positional_matchups = self.calculate_street_positional_matchups(dataframe, 'river')
        except Exception as e:
            print(f"Error calculating river positional matchups: {e}")
            river_positional_matchups = {}
        
        # Calculate overall positional matchups (combine all streets, use flop as primary since most hands reach flop)
        try:
            overall_positional_matchups = self.calculate_overall_positional_matchups(dataframe)
            # Ensure we always return a dict structure even if empty
            if not overall_positional_matchups:
                overall_positional_matchups = {}
            # If no pot types found or all are empty, use flop matchups as fallback
            if not overall_positional_matchups or all(not v or (isinstance(v, dict) and len(v) == 0) for v in overall_positional_matchups.values()):
                # Use flop matchups as overall, wrap in RFI Pots structure
                if flop_positional_matchups and isinstance(flop_positional_matchups, dict) and len(flop_positional_matchups) > 0:
                    overall_positional_matchups = {'RFI Pots': flop_positional_matchups}
                else:
                    # If even flop is empty, return empty dict (not a dict with empty dict inside)
                    overall_positional_matchups = {}
            # If no pot types found, at least return empty structure
            if not isinstance(overall_positional_matchups, dict):
                overall_positional_matchups = {}
            # Debug: print how many matchups were found
            total_matchups = sum(len(v) if isinstance(v, dict) else 0 for v in overall_positional_matchups.values())
            if total_matchups > 0:
                print(f"Generated {total_matchups} positional matchups across {len(overall_positional_matchups)} pot types")
        except Exception as e:
            print(f"Error calculating overall positional matchups: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: use flop matchups as overall, but wrap in RFI Pots structure
            if flop_positional_matchups and isinstance(flop_positional_matchups, dict) and len(flop_positional_matchups) > 0:
                overall_positional_matchups = {'RFI Pots': flop_positional_matchups}
            else:
                overall_positional_matchups = {}
        
        # Calculate biggest hands
        try:
            biggest_hands = self.calculate_biggest_hands(dataframe)
            # Debug: print how many hands were found
            total_biggest = len(biggest_hands.get('biggest_wins', [])) + len(biggest_hands.get('biggest_losses', []))
            if total_biggest > 0:
                print(f"Generated {len(biggest_hands.get('biggest_wins', []))} biggest wins and {len(biggest_hands.get('biggest_losses', []))} biggest losses")
        except Exception as e:
            print(f"Error calculating biggest hands: {e}")
            import traceback
            traceback.print_exc()
            biggest_hands = {'biggest_wins': [], 'biggest_losses': []}

        results['Session Earnings'] = round(earnings, 2)
        results['Session BB Earnings'] = round(BB_earnings, 2)
        results['BB per 100 hands'] = round(BB_earnings_per_100_hands, 2)
        results['Total Hands'] = number_of_hands  # Total hands in dataset
        results['VPIP Info'] = vpip
        results['RFI VPIP Info'] = vpip_rfi
        results['Positional Profitability'] = rounded_positional_profitability
        results['Three bet info'] = self.get_three_bet_metrics(df_six_players)
        results['IP Profitability'] = ip_profitability
        results['OP Profitability'] = op_profitability
        results['In Position Percentage'] = in_position_percentage
        results['Out Of Position Percentage'] = out_position_percentage
        results['Iso Raise info'] = self.get_iso_raise_metrics(dataframe)
        results['Flop High Card Analysis'] = flop_high_card
        results['Turn High Card Analysis'] = turn_high_card
        results['River High Card Analysis'] = river_high_card
        results['Board High Card Analysis'] = board_high_card
        results['Hand Matrix Analysis'] = hand_matrix
        results['Leak Detection'] = leaks
        results['Positional Matchups'] = overall_positional_matchups  # Overall matchups for boards and hands section
        results['Flop Positional Matchups'] = flop_positional_matchups
        results['Turn Positional Matchups'] = turn_positional_matchups
        results['River Positional Matchups'] = river_positional_matchups
        results['Biggest Hands'] = biggest_hands

        # Convert nested dicts to JSON strings so pandas can serialize them properly
        import json
        nested_keys = ['Flop High Card Analysis', 'Turn High Card Analysis', 'River High Card Analysis', 
                      'Board High Card Analysis', 'Hand Matrix Analysis', 'Leak Detection',
                      'Positional Matchups', 'Flop Positional Matchups', 'Turn Positional Matchups', 'River Positional Matchups',
                      'Biggest Hands',
                      'VPIP Info', 'RFI VPIP Info', 'Three bet info', 'Iso Raise info', 'Positional Profitability',
                      'Flop Action Frequency', 'Turn Action Frequency', 'River Action Frequency']
        
        results_for_df = {}
        for key, value in results.items():
            if key in nested_keys and isinstance(value, (dict, list)):
                results_for_df[key] = json.dumps(value)
            else:
                results_for_df[key] = value
        
        results_df = pd.DataFrame([results_for_df])

        return results_df

    def process_ladbrooks(self):
        try:
            is_valid, reason, processed_data = self.is_ladbrooks_hands()
            if not is_valid:
                return is_valid, reason, processed_data, 0
            dataframe = self.process_hands(processed_data)
            if dataframe is None or dataframe.empty:
                return False, "No valid hands could be processed", pd.DataFrame(), pd.DataFrame()
            results_df = self.advanced_processing(dataframe)
            if results_df is None or results_df.empty:
                return False, "Failed to generate results", dataframe, pd.DataFrame()
            return is_valid, reason, dataframe, results_df
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in process_ladbrooks: {str(e)}")
            print(f"Traceback: {error_details}")
            return False, f"Processing error: {str(e)}", pd.DataFrame(), pd.DataFrame()



