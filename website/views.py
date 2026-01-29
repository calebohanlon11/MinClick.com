# This file holds the main website pages and actions.
# It decides what users see and how posts and metrics are shown.
# It also includes admin tools like downloads and deletions.
from flask_login import login_required, current_user
import re
from .models import User, Comment, QuantMathResult, LiveSession, Post, QuizResult
from . import db
from .LadbrooksPokerHandProcessor import LadbrooksPokerHandProcessor


def _normalize_stake_value(value):
    formatted = f"{value:g}"
    return formatted[1:] if formatted.startswith("0.") else formatted


def _extract_stakes_from_hand(hand):
    stake_line = ""
    for line in hand.split("\n"):
        if "Texas Holdem Game Table" in line:
            stake_line = line.strip()
            break

    search_target = stake_line or hand
    header_match = re.search(
        r'\((?P<sb>[€£$]?\d+(?:\.\d+)?)\s*/\s*(?P<bb>[€£$]?\d+(?:\.\d+)?)\)',
        search_target
    )
    match = header_match or re.search(
        r'(?P<sb>[€£$]?\d+(?:\.\d+)?)\s*/\s*(?P<bb>[€£$]?\d+(?:\.\d+)?)',
        search_target
    )
    if match:
        def to_float(value):
            return float(re.sub(r'[^\d\.]', '', value))

        sb = to_float(match.group('sb'))
        bb = to_float(match.group('bb'))
        return sb, bb

    # Fallback: read blinds from action lines if header format is unexpected
    sb_match = re.search(r'posts small blind\s*\((?P<sb>\d+(?:\.\d+)?)\)', hand, re.IGNORECASE)
    bb_match = re.search(r'posts big blind\s*\((?P<bb>\d+(?:\.\d+)?)\)', hand, re.IGNORECASE)
    if sb_match and bb_match:
        return float(sb_match.group('sb')), float(bb_match.group('bb'))

    return None


def _format_stake_key(sb, bb):
    return f"{_normalize_stake_value(sb)}/{_normalize_stake_value(bb)}"


def _detect_stakes_in_file(self):
    stake_counts = {}
    for hand in self.split_hands():
        stakes = _extract_stakes_from_hand(hand)
        if not stakes:
            continue
        stake_key = _format_stake_key(*stakes)
        stake_counts[stake_key] = stake_counts.get(stake_key, 0) + 1
    return stake_counts


def _split_by_stakes(self):
    split_data = {}
    for hand in self.split_hands():
        stakes = _extract_stakes_from_hand(hand)
        if not stakes:
            continue
        stake_key = _format_stake_key(*stakes)
        split_data.setdefault(stake_key, []).append(hand)
    return {key: "\n".join(hands) for key, hands in split_data.items()}


if not hasattr(LadbrooksPokerHandProcessor, "detect_stakes_in_file"):
    LadbrooksPokerHandProcessor.detect_stakes_in_file = _detect_stakes_in_file

if not hasattr(LadbrooksPokerHandProcessor, "split_by_stakes"):
    LadbrooksPokerHandProcessor.split_by_stakes = _split_by_stakes
import json
import ast
import pandas as pd
from io import StringIO
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from datetime import datetime
from .Learning_question_generator import get_quantmath_questions
views = Blueprint("views", __name__)
import datetime

@views.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('views.all_posts'))
    return render_template('landing.html', user=current_user)

@views.route('/home')
def home():
    """Home page - shows landing page if not logged in, dashboard if logged in"""
    if current_user.is_authenticated:
        return render_template("home.html", user=current_user)
    else:
        return render_template('landing.html', user=current_user)

@views.route('/posts', defaults={'username': None})
@views.route('/posts/<username>')
@login_required
def all_posts(username=None):
    """Posts page with all post-related functionality"""
    if username:
        # View specific user's posts
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('No user with that username exists.', category='error')
            posts = Post.query.order_by(Post.date_created.desc()).all()
        else:
            posts = user.posts
            return render_template("posts.html", user=current_user, posts=posts, username=username)
    
    # View all posts
    posts = Post.query.order_by(Post.date_created.desc()).all()
    filter_applied = request.args.get('filter_applied')
    return render_template("posts.html", user=current_user, posts=posts, filter_applied=filter_applied)

@views.route('/filter', methods=['GET'])
@login_required
def filter_posts():
    stakes = request.args.getlist('stakes')
    site = request.args.get('site')
    my_sessions = request.args.get('my_sessions')

    query = Post.query
    if stakes:
        query = query.filter(Post.stake.in_(stakes))
    if site:
        query = query.filter_by(category=site)
    if my_sessions:
        query = query.filter_by(author=current_user.id)

    posts = query.order_by(Post.date_created.desc()).all()
    return render_template('posts.html', user=current_user, posts=posts, filter_applied=True)


@views.route("/view-metrics/<post_id>")
@login_required
def view_metrics(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if not post:
        flash("Post does not exist.", category='error')
        return redirect(url_for('views.all_posts'))

    # Parse the JSON string stored in data_frame_results and extract the dictionary
    try:
        metrics_list = json.loads(post.data_frame_results)
        if not metrics_list or not isinstance(metrics_list, list):
            flash("Invalid data format.", category='error')
            return redirect(url_for('views.all_posts'))

        # Extract the first dictionary from the list
        metrics = metrics_list[0]
        
        # Parse nested JSON strings back to dictionaries/lists
        nested_keys = ['Flop High Card Analysis', 'Turn High Card Analysis', 'River High Card Analysis', 
                      'Board High Card Analysis', 'Hand Matrix Analysis', 'Leak Detection',
                      'Positional Matchups', 'Flop Positional Matchups', 'Turn Positional Matchups', 'River Positional Matchups',
                      'Biggest Hands',
                      'VPIP Info', 'RFI VPIP Info', 'Three bet info', 'Four bet info', 'Iso Raise info', 'Positional Profitability',
                      'Flop Action Frequency', 'Turn Action Frequency', 'River Action Frequency']
        
        # Initialize action frequency keys if they don't exist (for old posts)
        for freq_key in ['Flop Action Frequency', 'Turn Action Frequency', 'River Action Frequency']:
            if freq_key not in metrics:
                metrics[freq_key] = {'total_hands': 0, 'ip': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0},
                                   'oop': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0},
                                   'multiway': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0}}
        
        for key in nested_keys:
            if key in metrics:
                value = metrics[key]
                # Check if it's a JSON string that needs parsing
                if isinstance(value, str) and len(value) > 0:
                    try:
                        # Try to parse as JSON
                        parsed = json.loads(value)
                        metrics[key] = parsed
                    except (json.JSONDecodeError, TypeError, ValueError):
                        # If parsing fails, check if it's already a dict/list
                        if isinstance(value, (dict, list)):
                            metrics[key] = value
                        # Otherwise leave as is (might be empty string or invalid)
                        pass
                # If it's already a dict/list, keep it
                elif isinstance(value, (dict, list)):
                    metrics[key] = value
                # If it's None or empty, set to empty dict/list
                elif value is None or value == '':
                    if key == 'Leak Detection' or 'Matchups' in key:
                        metrics[key] = {}
                    elif key == 'Biggest Hands':
                        metrics[key] = {'biggest_wins': [], 'biggest_losses': []}
                    elif key in ['Flop Action Frequency', 'Turn Action Frequency', 'River Action Frequency']:
                        # Ensure action frequency always has proper structure
                        metrics[key] = {'total_hands': 0, 'ip': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0},
                                       'oop': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0},
                                       'multiway': {'total': 0, 'checks': 0, 'bets': 0, 'calls': 0, 'folds': 0, 'raises': 0}}
                    else:
                        metrics[key] = {}
        
        # CRITICAL: After parsing VPIP Info, ensure it's a dict and initialize positional_hand_counts if missing
        # This must happen BEFORE the main calculation block to ensure the structure exists
        if 'VPIP Info' in metrics:
            if isinstance(metrics['VPIP Info'], str):
                try:
                    metrics['VPIP Info'] = json.loads(metrics['VPIP Info'])
                except:
                    metrics['VPIP Info'] = {}
            elif not isinstance(metrics['VPIP Info'], dict):
                metrics['VPIP Info'] = {}
            
            # Initialize positional_hand_counts as empty dict if it doesn't exist
            # This ensures the key exists even if calculation fails
            if 'positional_hand_counts' not in metrics['VPIP Info']:
                metrics['VPIP Info']['positional_hand_counts'] = {}
        
        # Ensure session earnings metrics are properly extracted and have default values
        # Handle potential NaN, None, or missing values from pandas JSON conversion
        import math
        
        # Helper function to safely convert to float, handling NaN, None, and string values
        def safe_float(value, default=0.0):
            if value is None:
                return default
            try:
                float_val = float(value)
                # Check for NaN (which can occur when pandas converts NaN to JSON null)
                if math.isnan(float_val):
                    return default
                return float_val
            except (ValueError, TypeError):
                return default
        
        if 'Session Earnings' not in metrics:
            metrics['Session Earnings'] = 0.0
        else:
            metrics['Session Earnings'] = safe_float(metrics.get('Session Earnings'), 0.0)
        
        if 'Session BB Earnings' not in metrics:
            metrics['Session BB Earnings'] = 0.0
        else:
            metrics['Session BB Earnings'] = safe_float(metrics.get('Session BB Earnings'), 0.0)
        
        if 'BB per 100 hands' not in metrics:
            metrics['BB per 100 hands'] = 0.0
        else:
            metrics['BB per 100 hands'] = safe_float(metrics.get('BB per 100 hands'), 0.0)

        # Ensure 3-bet/4-bet metrics are dicts (handle stored JSON strings)
        for bet_key in ['Three bet info', 'Four bet info']:
            if bet_key in metrics and isinstance(metrics.get(bet_key), str):
                try:
                    metrics[bet_key] = json.loads(metrics[bet_key])
                except Exception:
                    try:
                        metrics[bet_key] = ast.literal_eval(metrics[bet_key])
                    except Exception:
                        metrics[bet_key] = {}
            elif bet_key in metrics and metrics.get(bet_key) is None:
                metrics[bet_key] = {}

        # Normalize 3-bet/4-bet helpers so UI always has consistent denominators
        def ensure_standardized_three_bet(data):
            if not isinstance(data, dict):
                return {}
            branch_ev = data.get('branch_ev', {}) if isinstance(data.get('branch_ev'), dict) else {}
            villain_fold = data.get('villain_fold_vs_hero_3bet', 0)
            villain_call = data.get('villain_call_vs_hero_3bet', 0)
            villain_raise = data.get('villain_4bet_vs_hero_3bet', 0)
            if not any([villain_fold, villain_call, villain_raise]) and isinstance(branch_ev, dict):
                villain_fold = branch_ev.get('fold', {}).get('count', 0)
                villain_call = branch_ev.get('call', {}).get('count', 0)
                villain_raise = branch_ev.get('four_bet', {}).get('count', 0)
            if not any([villain_fold, villain_call, villain_raise]):
                by_hero_position = data.get('by_hero_position', {})
                if isinstance(by_hero_position, dict):
                    villain_fold = sum(pos_data.get('villain_fold', 0) for pos_data in by_hero_position.values() if isinstance(pos_data, dict))
                    villain_call = sum(pos_data.get('villain_call', 0) for pos_data in by_hero_position.values() if isinstance(pos_data, dict))
                    villain_raise = sum(pos_data.get('villain_4bet', 0) for pos_data in by_hero_position.values() if isinstance(pos_data, dict))
            data['standardized'] = {
                'facing_open_opportunities': data.get('hero_3bet_opportunities', 0),
                'hero_3bet_count': data.get('Num_three_bets', 0),
                'villain_response': {
                    'fold': villain_fold,
                    'call': villain_call,
                    'raise': villain_raise
                },
                'branch_ev': {
                    'fold': branch_ev.get('fold', {'count': 0, 'ev_bb': 0.0}),
                    'call': branch_ev.get('call', {'count': 0, 'ev_bb': 0.0}),
                    'raise': branch_ev.get('four_bet', {'count': 0, 'ev_bb': 0.0})
                },
                'hero_vs_raise': {
                    'fold': branch_ev.get('four_bet_hero_fold', {'count': 0, 'ev_bb': 0.0}),
                    'call': branch_ev.get('four_bet_hero_call', {'count': 0, 'ev_bb': 0.0}),
                    'jam': branch_ev.get('four_bet_hero_5bet', {'count': 0, 'ev_bb': 0.0})
                }
            }
            return data

        def ensure_standardized_four_bet(data):
            if not isinstance(data, dict):
                return {}
            branch_ev = data.get('branch_ev', {}) if isinstance(data.get('branch_ev'), dict) else {}
            villain_fold = data.get('villain_fold_vs_hero_4bet', 0)
            villain_call = data.get('villain_call_vs_hero_4bet', 0)
            villain_raise = data.get('villain_5bet_vs_hero_4bet', 0)
            if not any([villain_fold, villain_call, villain_raise]) and isinstance(branch_ev, dict):
                villain_fold = branch_ev.get('fold', {}).get('count', 0)
                villain_call = branch_ev.get('call', {}).get('count', 0)
                villain_raise = branch_ev.get('five_bet', {}).get('count', 0)
            if not any([villain_fold, villain_call, villain_raise]):
                by_hero_position = data.get('by_hero_position', {})
                if isinstance(by_hero_position, dict):
                    villain_fold = sum(pos_data.get('villain_fold', 0) for pos_data in by_hero_position.values() if isinstance(pos_data, dict))
                    villain_call = sum(pos_data.get('villain_call', 0) for pos_data in by_hero_position.values() if isinstance(pos_data, dict))
                    villain_raise = sum(pos_data.get('villain_5bet', 0) for pos_data in by_hero_position.values() if isinstance(pos_data, dict))
            data['standardized'] = {
                'facing_3bet_opportunities': data.get('hero_4bet_opportunities', 0),
                'hero_4bet_count': data.get('Num_four_bets', 0),
                'villain_response': {
                    'fold': villain_fold,
                    'call': villain_call,
                    'raise': villain_raise
                },
                'villain_raise_subtype': {
                    'jam': data.get('villain_5bet_jam_vs_hero_4bet', 0)
                },
                'branch_ev': {
                    'fold': branch_ev.get('fold', {'count': 0, 'ev_bb': 0.0}),
                    'call': branch_ev.get('call', {'count': 0, 'ev_bb': 0.0}),
                    'raise': branch_ev.get('five_bet', {'count': 0, 'ev_bb': 0.0})
                },
                'hero_vs_raise': {
                    'fold': branch_ev.get('five_bet_hero_fold', {'count': 0, 'ev_bb': 0.0}),
                    'call': branch_ev.get('five_bet_hero_call', {'count': 0, 'ev_bb': 0.0}),
                    'jam': branch_ev.get('five_bet_hero_jam', {'count': 0, 'ev_bb': 0.0})
                }
            }
            return data

        if 'Three bet info' in metrics:
            metrics['Three bet info'] = ensure_standardized_three_bet(metrics.get('Three bet info'))
        if 'Four bet info' in metrics:
            metrics['Four bet info'] = ensure_standardized_four_bet(metrics.get('Four bet info'))
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        flash("Error reading post data. You may need to reprocess this post.", category='error')
        return redirect(url_for('views.all_posts'))
    
    # ALWAYS calculate positional_hand_counts from dataframe to ensure accuracy
    # This ensures hand counts are always available, even for old data
    # IMPORTANT: Do this AFTER all JSON parsing is complete
    # Ensure VPIP Info exists - create it if it doesn't
    if 'VPIP Info' not in metrics:
        metrics['VPIP Info'] = {}
    
    if 'VPIP Info' in metrics:
        # Ensure VPIP Info is a dictionary (not a string)
        if isinstance(metrics['VPIP Info'], str):
            try:
                metrics['VPIP Info'] = json.loads(metrics['VPIP Info'])
            except:
                metrics['VPIP Info'] = {}
        elif not isinstance(metrics['VPIP Info'], dict):
            metrics['VPIP Info'] = {}
        
        # Always recalculate from dataframe - don't trust stored values
        try:
            import pandas as pd
            from io import StringIO
            if post.data_frame:
                df = pd.read_json(StringIO(post.data_frame), orient='records')
                if not df.empty and 'position' in df.columns:
                    # Count ALL hands by position (not just VPIP hands)
                    position_hand_counts = df['position'].value_counts()
                    ordered_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
                    position_hand_counts_ordered = position_hand_counts.reindex(ordered_positions).fillna(0)
                    # Convert to dictionary with integer counts
                    hand_counts_dict = {pos: int(count) for pos, count in position_hand_counts_ordered.to_dict().items()}
                    # CRITICAL: Directly assign to the dict - don't use update, replace entirely
                    metrics['VPIP Info']['positional_hand_counts'] = hand_counts_dict
                    print(f"DEBUG: Set positional_hand_counts = {hand_counts_dict}")

                    # Ensure JSON string fields are parsed before using them
                    if isinstance(metrics.get('Turn Action Frequency'), str):
                        try:
                            metrics['Turn Action Frequency'] = json.loads(metrics['Turn Action Frequency'])
                        except Exception:
                            metrics['Turn Action Frequency'] = {}
                    if isinstance(metrics.get('River Action Frequency'), str):
                        try:
                            metrics['River Action Frequency'] = json.loads(metrics['River Action Frequency'])
                        except Exception:
                            metrics['River Action Frequency'] = {}
                    if isinstance(metrics.get('Positional Matchups'), str):
                        try:
                            metrics['Positional Matchups'] = json.loads(metrics['Positional Matchups'])
                        except Exception:
                            metrics['Positional Matchups'] = {}


                    # Refresh turn/river bet rate scenarios from dataframe to avoid stale zeros
                    try:
                        processor = LadbrooksPokerHandProcessor("")
                        metrics.update(processor.calculate_bet_rates(df, 'turn'))
                        metrics.update(processor.calculate_bet_rates(df, 'river'))
                    except Exception as e:
                        print(f"ERROR recalculating bet rates: {e}")

                    # If positional matchups are missing or empty, rebuild from dataframe
                    try:
                        positional_matchups = metrics.get('Positional Matchups', {})
                        if not positional_matchups or not isinstance(positional_matchups, dict):
                            positional_matchups = {}
                        if not positional_matchups:
                            processor = LadbrooksPokerHandProcessor("")
                            metrics['Positional Matchups'] = processor.calculate_overall_positional_matchups(df)
                    except Exception as e:
                        print(f"ERROR recalculating positional matchups: {e}")
                # Recalculate turn/river totals from dataframe to ensure accuracy
                def _street_total_from_df(df, street):
                    if street not in ['turn', 'river']:
                        return None
                    active_col = f'hero_is_active_on_{street}'
                    saw_col = f'hero_saw_{street}'
                    flop_active_col = 'hero_is_active_on_flop'
                    flop_saw_col = 'hero_saw_flop'

                    if active_col in df.columns:
                        mask = (df[active_col] == True)
                    elif saw_col in df.columns:
                        mask = (df[saw_col] == True)
                    else:
                        # Fallback: derive from raw hand history
                        if 'Raw Hand' not in df.columns:
                            return None
                        street_marker = '** Dealing Turn **' if street == 'turn' else '** Dealing River **'

                        def hero_reached_turn_or_river(raw_hand):
                            if not raw_hand or street_marker not in raw_hand or '** Dealing Flop **' not in raw_hand:
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
                            if street == 'river':
                                # Turn: Hero must not fold before river
                                if '** Dealing Turn **' not in raw_hand:
                                    return False
                                turn_section = raw_hand.split('** Dealing Turn **')[1]
                                if '** Dealing River **' in turn_section:
                                    turn_section = turn_section.split('** Dealing River **')[0]
                                elif '** Summary **' in turn_section:
                                    turn_section = turn_section.split('** Summary **')[0]
                                if 'Hero folds' in turn_section:
                                    return False
                            return True

                        return int(df['Raw Hand'].apply(hero_reached_turn_or_river).sum())

                    # Ensure Hero also reached the flop
                    if flop_active_col in df.columns:
                        mask = mask & (df[flop_active_col] == True)
                    elif flop_saw_col in df.columns:
                        mask = mask & (df[flop_saw_col] == True)

                    return int(mask.sum())

                turn_total = _street_total_from_df(df, 'turn')
                if turn_total is not None:
                    if 'Turn Action Frequency' not in metrics or not isinstance(metrics['Turn Action Frequency'], dict):
                        metrics['Turn Action Frequency'] = {}
                    metrics['Turn Action Frequency']['total_hands'] = turn_total
                    print(f"DEBUG: Recalculated Turn Action Frequency total_hands = {turn_total}")

                river_total = _street_total_from_df(df, 'river')
                if river_total is not None:
                    if 'River Action Frequency' not in metrics or not isinstance(metrics['River Action Frequency'], dict):
                        metrics['River Action Frequency'] = {}
                    metrics['River Action Frequency']['total_hands'] = river_total
                    print(f"DEBUG: Recalculated River Action Frequency total_hands = {river_total}")

                if df.empty or 'position' not in df.columns:
                    # DataFrame is empty or missing position column - set defaults
                    metrics['VPIP Info']['positional_hand_counts'] = {pos: 0 for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']}
                    print(f"DEBUG: DataFrame empty or missing position column, set defaults")
            else:
                # No dataframe available - set defaults
                metrics['VPIP Info']['positional_hand_counts'] = {pos: 0 for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']}
                print(f"DEBUG: No dataframe available, set defaults")
        except Exception as e:
            # If calculation fails, ensure defaults exist
            import traceback
            print(f"ERROR calculating positional_hand_counts: {e}")
            print(traceback.format_exc())
            metrics['VPIP Info']['positional_hand_counts'] = {pos: 0 for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']}
    
    # Final verification before template
    if 'VPIP Info' in metrics and 'positional_hand_counts' in metrics['VPIP Info']:
        final_counts = metrics['VPIP Info']['positional_hand_counts']
        print(f"=" * 80)
        print(f"DEBUG: Final check - positional_hand_counts = {final_counts}")
        print(f"DEBUG: Values that template should see:")
        for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']:
            print(f"  {pos}: {final_counts.get(pos, 0)}")
        print(f"=" * 80)
    else:
        print(f"=" * 80)
        print(f"DEBUG: Final check - positional_hand_counts MISSING!")
        print(f"VPIP Info exists: {'VPIP Info' in metrics}")
        if 'VPIP Info' in metrics:
            print(f"VPIP Info type: {type(metrics['VPIP Info'])}")
            print(f"VPIP Info keys: {list(metrics['VPIP Info'].keys()) if isinstance(metrics['VPIP Info'], dict) else 'N/A'}")
        print(f"=" * 80)
    
    # Final safety check - ensure it exists before passing to template
    if 'VPIP Info' in metrics:
        if 'positional_hand_counts' not in metrics['VPIP Info'] or not metrics['VPIP Info'].get('positional_hand_counts'):
            # Last resort: try to calculate one more time
            try:
                import pandas as pd
                from io import StringIO
                if post.data_frame:
                    df = pd.read_json(StringIO(post.data_frame), orient='records')
                    if not df.empty and 'position' in df.columns:
                        position_hand_counts = df['position'].value_counts()
                        ordered_positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
                        position_hand_counts_ordered = position_hand_counts.reindex(ordered_positions).fillna(0)
                        hand_counts_dict = {pos: int(count) for pos, count in position_hand_counts_ordered.to_dict().items()}
                        metrics['VPIP Info']['positional_hand_counts'] = hand_counts_dict
                    else:
                        metrics['VPIP Info']['positional_hand_counts'] = {pos: 0 for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']}
                else:
                    metrics['VPIP Info']['positional_hand_counts'] = {pos: 0 for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']}
            except:
                metrics['VPIP Info']['positional_hand_counts'] = {pos: 0 for pos in ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']}

    return render_template("view_metrics.html", metrics=metrics, user=current_user, post_id=post_id)


@views.route('/create-post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == "POST":
        if current_user.username == 'guest':
            flash('Guests cannot create a post', category='error')
            return redirect(url_for('views.create_post'))
        text = request.form.get('text')
        file = request.files.get('file')
        category = request.form.get('category')
        stake = request.form.get('stake')
        
        # Get new game information fields
        game_type = request.form.get('game_type')  # 'cash' or 'tournament'
        table_size = request.form.get('table_size', '').strip() or None
        game_name = request.form.get('game_name', '').strip() or None
        buy_in = request.form.get('buy_in')
        buy_in = float(buy_in) if buy_in else None
        cash_out = request.form.get('cash_out')
        cash_out = float(cash_out) if cash_out else None
        currency = request.form.get('currency', 'USD')

        if not text:
            flash('Post cannot be empty', category='error')
        elif not file or file.filename == '':
            flash('File is required', category='error')
        elif file.filename.endswith('.txt'):

            if len(file.read()) > 10 * 1024 * 1024:
                flash('File size cannot exceed 10MB', category='error')
                return redirect(url_for('views.create_post'))

            file.seek(0)
            file_data = file.read().decode('utf-8')  # Read file contents as string

            if category == 'ladbrooks':
                # First, detect all stake levels in the file
                temp_processor = LadbrooksPokerHandProcessor(file_data)
                stake_levels = {}
                for hand in temp_processor.split_hands():
                    stakes = _extract_stakes_from_hand(hand)
                    if not stakes:
                        continue
                    stake_key = _format_stake_key(*stakes)
                    stake_levels[stake_key] = stake_levels.get(stake_key, 0) + 1
                
                if not stake_levels:
                    flash('No valid stake levels detected in the file', category='error')
                    return redirect(url_for('views.create_post'))
                
                # Split file by stakes if multiple stakes found
                if len(stake_levels) > 1:
                    split_data = {}
                    for hand in temp_processor.split_hands():
                        stakes = _extract_stakes_from_hand(hand)
                        if not stakes:
                            continue
                        stake_key = _format_stake_key(*stakes)
                        split_data.setdefault(stake_key, []).append(hand)
                    split_data = {key: "\n".join(hands) for key, hands in split_data.items()}
                    posts_created = []
                    
                    for stake_key, stake_file_data in split_data.items():
                        # Process each stake level separately
                        stake_processor = LadbrooksPokerHandProcessor(stake_file_data)
                        is_real_dataset, reason, processed_dataframe, results = stake_processor.process_ladbrooks()
                        
                        if not is_real_dataset:
                            flash(f'Error processing stake {stake_key}: {reason}', category='error')
                            continue
                        
                        # Check if dataframe is empty (no valid hands for this stake)
                        if processed_dataframe.empty or len(processed_dataframe) == 0:
                            flash(f'No valid hands found for stake {stake_key}. Skipping.', category='warning')
                            continue
                        
                        df_json = processed_dataframe.to_json(orient='records')
                        df_results_json = results.to_json(orient='records')
                        
                        # Create post text with stake information
                        post_text = f"{text}\n\n[Stake: {stake_key}]"
                        
                        post = Post(
                            text=post_text, 
                            author=current_user.id, 
                            file_data=stake_file_data.encode('utf-8'),
                            data_frame=df_json, 
                            data_frame_results=df_results_json,
                            category=category, 
                            stake=stake_key,
                            game_type=game_type,
                            table_size=table_size,
                            game_name=game_name,
                            buy_in=buy_in,
                            cash_out=cash_out,
                            currency=currency
                        )
                        db.session.add(post)
                        posts_created.append(stake_key)
                    
                    db.session.commit()
                    
                    if posts_created:
                        flash(f'Successfully created {len(posts_created)} post(s) for stakes: {", ".join(posts_created)}', category='success')
                        return redirect(url_for('views.all_posts'))
                    else:
                        flash('Failed to create any posts', category='error')
                        return redirect(url_for('views.create_post'))
                else:
                    # Single stake level - process normally
                    stake_key = list(stake_levels.keys())[0]
                ladbrooks_processor = LadbrooksPokerHandProcessor(file_data)
                is_real_dataset, reason, processed_dataframe, results = ladbrooks_processor.process_ladbrooks()

                if not is_real_dataset:
                    flash(reason, category='error')
                    return redirect(url_for('views.create_post'))

                df_json = processed_dataframe.to_json(orient='records')
                df_results_json = results.to_json(orient='records')

                post = Post(
                        text=text, 
                        author=current_user.id, 
                        file_data=file_data.encode('utf-8'),
                        data_frame=df_json, 
                        data_frame_results=df_results_json,
                        category=category, 
                        stake=stake_key,
                        game_type=game_type,
                        table_size=table_size,
                        game_name=game_name,
                        buy_in=buy_in,
                        cash_out=cash_out,
                        currency=currency
                    )
                db.session.add(post)
                db.session.commit()
                flash(f'Post created successfully! (Stake: {stake_key})', category='success')
                return redirect(url_for('views.all_posts'))
            else:
                flash('No Poker Site selected', category='error')
        else:
            flash('File must be a .txt file', category='error')

    return render_template('create_post.html', user=current_user)

@views.route("/view-file/<post_id>")
@login_required
def view_file(post_id):
    post = Post.query.filter_by(id=post_id).first()

    if not post or not post.file_data:
        flash('File does not exist.', category='error')
        return redirect(url_for('views.all_posts'))

    file_contents = post.file_data.decode('utf-8')  # Assuming the file is a text file
    return render_template("view_file.html", file_contents=file_contents, user=current_user)


@views.route("/view-dataframe/<post_id>")
@login_required
def view_dataframe(post_id):
    post = Post.query.filter_by(id=post_id).first()

    if not post or not post.data_frame_results:
        flash('Data frame results do not exist.', category='error')
        return redirect(url_for('views.all_posts'))

    # Wrap the JSON string in a StringIO object
    df = pd.read_json(StringIO(post.data_frame_results), orient='records')
    csv_data = df.to_csv(index=False)

    return render_template("view_dataframe.html", csv_data=csv_data, user=current_user)


@views.route("/reprocess-post/<post_id>")
@login_required
def reprocess_post(post_id):
    """Reprocess an existing post with updated analysis functions"""
    post = Post.query.filter_by(id=post_id).first()

    if not post:
        flash("Post does not exist.", category='error')
        return redirect(url_for('views.all_posts'))
    
    if current_user.id != post.author and not current_user.admin:
        flash('You do not have permission to reprocess this post.', category='error')
        return redirect(url_for('views.all_posts'))
    
    if not post.file_data:
        flash('Post does not have file data to reprocess.', category='error')
        return redirect(url_for('views.all_posts'))
    
    try:
        # Get the original file data
        file_data = post.file_data.decode('utf-8')
        
        # Reprocess with updated analysis
        if post.category == 'ladbrooks':
            ladbrooks_processor = LadbrooksPokerHandProcessor(file_data)
            is_real_dataset, reason, processed_dataframe, results = ladbrooks_processor.process_ladbrooks()
            
            if not is_real_dataset:
                flash(f'Reprocessing failed: {reason}', category='error')
                return redirect(url_for('views.all_posts'))
            
            # Check if dataframe is empty
            if processed_dataframe.empty or len(processed_dataframe) == 0:
                flash('Reprocessing failed: No valid hands found in the file.', category='error')
                return redirect(url_for('views.all_posts'))
            
            # Check if results are empty
            if results.empty or len(results) == 0:
                flash('Reprocessing failed: No results generated.', category='error')
                return redirect(url_for('views.all_posts'))
            
            # Update the post with new results
            df_json = processed_dataframe.to_json(orient='records')
            df_results_json = results.to_json(orient='records')
            
            post.data_frame = df_json
            post.data_frame_results = df_results_json
            db.session.commit()
            
            flash('Post reprocessed successfully with updated analytics!', category='success')
            return redirect(url_for('views.view_metrics', post_id=post_id))
        else:
            flash('Reprocessing is only available for Ladbrooks posts.', category='error')
            return redirect(url_for('views.all_posts'))
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        flash(f'Error reprocessing post: {str(e)}. Details: {error_details[:200]}', category='error')
        return redirect(url_for('views.all_posts'))


@views.route("/diagnose-post/<post_id>")
@login_required
def diagnose_post(post_id):
    """Diagnostic endpoint to see what's wrong with a post"""
    post = Post.query.filter_by(id=post_id).first()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    if current_user.id != post.author and not current_user.admin:
        return jsonify({'error': 'Permission denied'}), 403
    
    diagnostics = {
        'post_id': post.id,
        'has_file_data': post.file_data is not None,
        'file_data_length': len(post.file_data) if post.file_data else 0,
        'category': post.category,
        'has_data_frame': post.data_frame is not None,
        'has_data_frame_results': post.data_frame_results is not None,
    }
    
    # Try to decode file data
    if post.file_data:
        try:
            file_data = post.file_data.decode('utf-8')
            diagnostics['file_data_decoded'] = True
            diagnostics['file_data_preview'] = file_data[:200] if len(file_data) > 200 else file_data
            diagnostics['file_data_has_hands'] = '***** Hand History For Game' in file_data
            
            # Try to process
            try:
                ladbrooks_processor = LadbrooksPokerHandProcessor(file_data)
                is_real_dataset, reason, processed_dataframe, results = ladbrooks_processor.process_ladbrooks()
                diagnostics['processing_attempted'] = True
                diagnostics['is_real_dataset'] = is_real_dataset
                diagnostics['processing_reason'] = reason
                diagnostics['dataframe_rows'] = len(processed_dataframe) if processed_dataframe is not None else 0
                diagnostics['results_rows'] = len(results) if results is not None else 0
            except Exception as e:
                diagnostics['processing_error'] = str(e)
                diagnostics['processing_traceback'] = str(e.__class__.__name__)
        except Exception as e:
            diagnostics['decode_error'] = str(e)
    
    return jsonify(diagnostics)


@views.route("/reprocess-all-posts", methods=['POST'])
@login_required
def reprocess_all_posts():
    """Reprocess all posts belonging to the current user"""
    try:
        print(f"\n{'='*80}")
        print(f"REPROCESS REQUEST - User ID: {current_user.id}, Username: {current_user.username}")
        print(f"{'='*80}\n")
        
        # Get all posts belonging to the current user that have file data
        user_posts = Post.query.filter_by(author=current_user.id).filter(
            Post.file_data.isnot(None),
            Post.category == 'ladbrooks'
        ).all()
        
        print(f"Found {len(user_posts)} posts for user {current_user.id}")
        
        # Also check if there are posts for other users (for debugging)
        all_ladbrooks_posts = Post.query.filter(
            Post.file_data.isnot(None),
            Post.category == 'ladbrooks'
        ).all()
        if len(all_ladbrooks_posts) > len(user_posts):
            other_users_posts = [p for p in all_ladbrooks_posts if p.author != current_user.id]
            if other_users_posts:
                other_user_ids = set(p.author for p in other_users_posts)
                print(f"WARNING: Found {len(other_users_posts)} posts owned by other users: {other_user_ids}")
                print(f"  These posts belong to: {[User.query.get(uid).username for uid in other_user_ids if User.query.get(uid)]}")
        
        if not user_posts:
            flash('No posts found to reprocess. Make sure you are logged in as the user who created the posts.', category='info')
            print("No posts found - redirecting")
            return redirect(url_for('views.all_posts'))
        
        reprocessed_count = 0
        failed_count = 0
        error_details_list = []  # Store all errors for display
        failed_posts = []  # Track which posts failed
        
        print(f"\n{'='*80}")
        print(f"Starting reprocessing of {len(user_posts)} post(s)...")
        print(f"{'='*80}\n")
        
        for post in user_posts:
            try:
                print(f"Processing post {post.id}...")
                
                # Validate post has file data
                if not post.file_data:
                    failed_count += 1
                    failed_posts.append(post.id)
                    error_msg = f"Post {post.id}: No file data found"
                    error_details_list.append(f"Post {post.id}: No file data found")
                    print(f"  ✗ {error_msg}")
                    flash(f'Post {post.id}: No file data', category='error')
                    continue
                
                # Get the original file data
                try:
                    file_data = post.file_data.decode('utf-8')
                except Exception as decode_error:
                    failed_count += 1
                    failed_posts.append(post.id)
                    error_msg = f"Post {post.id}: Failed to decode file data - {str(decode_error)}"
                    error_details_list.append(f"Post {post.id}: Decode error - {str(decode_error)[:150]}")
                    print(f"  ✗ {error_msg}")
                    flash(f'Post {post.id}: File decode error', category='error')
                    continue
                
                if not file_data or len(file_data.strip()) == 0:
                    failed_count += 1
                    failed_posts.append(post.id)
                    error_msg = f"Post {post.id}: File data is empty"
                    error_details_list.append(f"Post {post.id}: File data is empty")
                    print(f"  ✗ {error_msg}")
                    flash(f'Post {post.id}: Empty file data', category='error')
                    continue
                
                # Reprocess with updated analysis
                try:
                    print(f"  Creating processor for post {post.id}...")
                    ladbrooks_processor = LadbrooksPokerHandProcessor(file_data)
                    print(f"  Calling process_ladbrooks() for post {post.id}...")
                    is_real_dataset, reason, processed_dataframe, results = ladbrooks_processor.process_ladbrooks()
                    print(f"  process_ladbrooks() returned: is_real={is_real_dataset}, reason={reason[:50] if reason else 'None'}")
                except Exception as process_error:
                    failed_count += 1
                    failed_posts.append(post.id)
                    import traceback
                    error_details = traceback.format_exc()
                    error_type = type(process_error).__name__
                    error_msg = f"Post {post.id}: Processing failed ({error_type}): {str(process_error)}"
                    error_details_list.append(f"Post {post.id}: {error_type} - {str(process_error)[:200]}")
                    print(f"  ✗ {error_msg}")
                    print(f"  Full traceback:")
                    print(error_details)
                    flash(f'Post {post.id}: {error_type}: {str(process_error)[:100]}', category='error')
                    continue
                
                if not is_real_dataset:
                    failed_count += 1
                    failed_posts.append(post.id)
                    error_msg = f"Post {post.id}: Not a valid dataset - {reason}"
                    error_details_list.append(f"Post {post.id}: Invalid dataset - {reason}")
                    print(f"  ✗ {error_msg}")
                    flash(f'Post {post.id}: {reason[:100]}', category='error')
                    continue
                
                # Validate dataframes
                if processed_dataframe is None or processed_dataframe.empty:
                    failed_count += 1
                    failed_posts.append(post.id)
                    error_msg = f"Post {post.id}: Processed dataframe is empty"
                    error_details_list.append(f"Post {post.id}: No valid hands found")
                    print(f"  ✗ {error_msg}")
                    flash(f'Post {post.id}: No valid hands found', category='error')
                    continue
                
                if results is None or results.empty:
                    failed_count += 1
                    failed_posts.append(post.id)
                    error_msg = f"Post {post.id}: Results dataframe is empty"
                    error_details_list.append(f"Post {post.id}: No results generated")
                    print(f"  ✗ {error_msg}")
                    flash(f'Post {post.id}: No results generated', category='error')
                    continue
                
                # Update the post with new results
                try:
                    print(f"  Converting to JSON for post {post.id}...")
                    df_json = processed_dataframe.to_json(orient='records')
                    df_results_json = results.to_json(orient='records')
                    print(f"  JSON conversion successful (df: {len(df_json)} chars, results: {len(df_results_json)} chars)")
                    
                    print(f"  Updating post {post.id} in database...")
                    post.data_frame = df_json
                    post.data_frame_results = df_results_json
                    print(f"  Post {post.id} updated in session (not yet committed)")
                    reprocessed_count += 1
                    print(f"  [SUCCESS] Post {post.id} reprocessed ({len(processed_dataframe)} hands)")
                except Exception as json_error:
                    failed_count += 1
                    failed_posts.append(post.id)
                    error_msg = f"Post {post.id}: Failed to convert to JSON - {str(json_error)}"
                    error_details_list.append(f"Post {post.id}: JSON error - {str(json_error)[:150]}")
                    print(f"  [FAILED] {error_msg}")
                    import traceback
                    print(traceback.format_exc())
                    flash(f'Post {post.id}: JSON conversion error', category='error')
                    continue
                
            except Exception as e:
                failed_count += 1
                failed_posts.append(post.id)
                import traceback
                error_details = traceback.format_exc()
                error_msg = f"Post {post.id}: Unexpected error - {str(e)}"
                error_details_list.append(f"Post {post.id}: Unexpected error - {str(e)[:200]}")
                print(f"  ✗ {error_msg}")
                print(f"  Traceback (first 500 chars): {error_details[:500]}")
                flash(f'Post {post.id}: {str(e)[:200]}', category='error')
                continue
        
        # Commit all changes at once
        try:
            db.session.commit()
            print(f"[OK] Database commit successful")
        except Exception as commit_error:
            print(f"[FAILED] Database commit failed: {str(commit_error)}")
            import traceback
            print(traceback.format_exc())
            db.session.rollback()
            failed_count += reprocessed_count  # Count successful processing as failed if commit fails
            reprocessed_count = 0
            error_details_list.append(f"Database commit failed: {str(commit_error)[:200]}")
            flash(f'Database error during commit: {str(commit_error)[:200]}', category='error')
        
        if reprocessed_count > 0:
            flash(f'Successfully reprocessed {reprocessed_count} post(s)!', category='success')
        print(f"\n{'='*80}")
        print(f"Reprocessing complete: {reprocessed_count} succeeded, {failed_count} failed")
        print(f"{'='*80}\n")
        
        if failed_count > 0:
            # Always print to console first - make it VERY visible
            print("\n\n")
            print("!" * 80)
            print("!" * 80)
            print("REPROCESSING ERRORS - CHECK THIS OUTPUT!")
            print("!" * 80)
            print("!" * 80)
            print(f"Total failed: {failed_count}")
            print(f"Failed post IDs: {failed_posts}")
            print(f"Errors collected: {len(error_details_list)}")
            print("-" * 80)
            if error_details_list:
                for i, error in enumerate(error_details_list, 1):
                    print(f"ERROR {i}: {error}")
            else:
                print("WARNING: No error details were collected!")
                print("This might indicate an error occurred before error collection.")
                print("Check the individual error messages printed above for each post.")
            print("!" * 80)
            print("!" * 80)
            print("\n\n")
            
            # Store errors in session for potential future display
            try:
                session['last_reprocess_errors'] = {
                    'failed_count': failed_count,
                    'failed_posts': failed_posts,
                    'errors': error_details_list[:10]  # Store first 10 errors
                }
            except:
                pass  # Session might not be available
            
            # Create flash message - SIMPLIFIED to always show post IDs
            # Build message in parts to ensure it's always informative
            msg = f"Failed to reprocess {failed_count} post(s)"
            
            # Always add post IDs if we have them
            if failed_posts:
                ids_str = ", ".join([str(p) for p in failed_posts])
                msg += f" (IDs: {ids_str})"
            
            # Add error details if available
            if error_details_list and len(error_details_list) > 0:
                first_err = error_details_list[0]
                # Truncate if needed but keep it visible
                if len(first_err) > 100:
                    first_err = first_err[:97] + "..."
                msg += f". Error: {first_err}"
                if len(error_details_list) > 1:
                    msg += f" (+{len(error_details_list)-1} more)"
            else:
                msg += ". See console for details"
            
            # Flash multiple messages to ensure visibility
            flash(msg, category='warning')
            
            # Also flash a second message with just the post IDs for visibility
            if failed_posts:
                flash(f"Failed Post IDs: {', '.join(map(str, failed_posts))}", category='error')
        
        return redirect(url_for('views.all_posts'))
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f'CRITICAL ERROR in reprocess_all_posts: {str(e)}'
        print("\n" + "!" * 80)
        print("CRITICAL ERROR - Top level exception caught!")
        print("!" * 80)
        print(error_msg)
        print("Full traceback:")
        print(error_details)
        print("!" * 80 + "\n")
        flash(f'Critical error: {str(e)[:200]}', category='error')
        return redirect(url_for('views.all_posts'))


@views.route("/delete-post/<id>")
@login_required
def delete_post(id):
    post = Post.query.filter_by(id=id).first()

    if not post:
        flash("Post does not exist.", category='error')
    elif current_user.id != post.author:
        flash('You do not have permission to delete this post.', category='error')
    else:
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted.', category='success')

    return redirect(url_for('views.all_posts'))





@views.route("/create-comment/<post_id>", methods=['POST'])
@login_required
def create_comment(post_id):

    if current_user.username == 'guest':
        flash('Guests cannot comment', category='error')
        return redirect(url_for('views.all_posts'))

    text = request.form.get('text')

    if not text:
        flash('Comment cannot be empty.', category='error')
    else:
        post = Post.query.filter_by(id=post_id)
        if post:
            comment = Comment(
                text=text, author=current_user.id, post_id=post_id)
            db.session.add(comment)
            db.session.commit()
        else:
            flash('Post does not exist.', category='error')

    return redirect(url_for('views.all_posts'))


@views.route("/delete-comment/<comment_id>")
@login_required
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()

    if not comment:
        flash('Comment does not exist.', category='error')
    elif current_user.id != comment.author and current_user.id != comment.post.author:
        flash('You do not have permission to delete this comment.', category='error')
    else:
        db.session.delete(comment)
        db.session.commit()

    return redirect(url_for('views.all_posts'))





@views.route("/make_admin", methods=['POST'])
@login_required
def make_admin():
    if not current_user.admin:
        flash('You are not authorized to perform this action.', category='error')
        return redirect(url_for('views.all_posts'))

    user_id = request.form.get('make_admin_id')
    user = User.query.get(user_id)
    if user:
        user.admin = True
        db.session.commit()
        flash(f'{user.username} is now an admin.', category='success')
    else:
        flash('User not found.', category='error')

    return redirect(url_for('views.admin'))


@views.route("/delete_user", methods=['POST'])
@login_required
def delete_user():
    if not current_user.admin:
        flash('You are not authorized to perform this action.', category='error')
        return redirect(url_for('views.all_posts'))

    user_id = request.form.get('delete_user_id')
    user = User.query.get(user_id)
    if user:
        # Delete all comments by the user
        Comment.query.filter_by(author=user.id).delete()
        # Delete all posts by the user (which will also delete associated comments)
        Post.query.filter_by(author=user.id).delete()
        # Finally, delete the user
        db.session.delete(user)
        db.session.commit()
        flash(f'{user.username} has been deleted along with their posts and comments.', category='success')
    else:
        flash('User not found.', category='error')

    return redirect(url_for('views.admin'))


@views.route("/admin", methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.admin:
        flash('You are not authorized to access this page.', category='error')
        return redirect(url_for('views.all_posts'))

    search_query = request.form.get('search_query')
    users = None
    selected_user = None
    user_posts = None

    if search_query:
        users = User.query.filter(User.username.contains(search_query) | User.email.contains(search_query)).all()

    selected_user_id = request.form.get('selected_user_id')
    if selected_user_id:
        selected_user = User.query.get(selected_user_id)
        user_posts = Post.query.filter_by(author=selected_user.id).order_by(Post.date_created.desc()).all()

    return render_template("admin.html", user=current_user, users=users, selected_user=selected_user, posts=user_posts)


from flask import send_file, redirect, url_for, flash
from .tcdcards_data import export_poker_members_to_csv


@views.route('/download-members', methods=['GET'])
@login_required
def download_members():
    if not current_user.admin:
        flash('You are not authorized to perform this action.', category='error')
        return redirect(url_for('views.all_posts'))

    # Define the file path
    file_path = 'poker_members.csv'

    # Call the function to export to CSV
    export_poker_members_to_csv()

    # Send the CSV file to the user
    return send_file(file_path, as_attachment=True)


@views.route("/admin_delete_post", methods=['POST'])
@login_required
def admin_delete_post():
    if not current_user.admin:
        flash('You are not authorized to perform this action.', category='error')
        return redirect(url_for('views.all_posts'))

    post_id = request.form.get('post_id')
    post = Post.query.get(post_id)
    if post:
        db.session.delete(post)
        db.session.commit()
        flash('Post has been deleted.', category='success')
    else:
        flash('Post not found.', category='error')

    return redirect(url_for('views.admin'))


@views.route("/admin_delete_comment", methods=['POST'])
@login_required
def admin_delete_comment():
    if not current_user.admin:
        flash('You are not authorized to perform this action.', category='error')
        return redirect(url_for('views.all_posts'))

    comment_id = request.form.get('comment_id')
    comment = Comment.query.get(comment_id)
    if comment:
        db.session.delete(comment)
        db.session.commit()
        flash('Comment has been deleted.', category='success')
    else:
        flash('Comment not found.', category='error')

    return redirect(url_for('views.admin'))


@views.route('/learning')
@login_required
def learning():
    return render_template('learning_base.html', user=current_user)


@views.route('/complete_signup')
def complete_signup():

    return render_template('complete_sign_up.html', user=current_user)


def calculate_bankroll_data(user_id):
    """Calculate comprehensive bankroll data for cash games only (online + live)"""
    from datetime import datetime, timedelta
    from calendar import monthrange
    
    # Currency conversion rate (EUR to USD) - inverse of USD_TO_EUR_RATE
    EUR_TO_USD_RATE = 1 / 0.92  # Approximately 1.087
    
    # Get all cash game posts (online)
    user_posts = Post.query.filter_by(author=user_id).order_by(Post.date_created.asc()).all()
    
    # Get all live sessions
    live_sessions = LiveSession.query.filter_by(user_id=user_id).order_by(LiveSession.session_date.asc()).all()
    
    if not user_posts and not live_sessions:
        return None
    
    # Current date for calculations
    now = datetime.now()
    current_month_start = datetime(now.year, now.month, 1)
    
    # Initialize totals
    total_earnings = 0.0
    total_bb_earnings = 0.0
    total_hands = 0
    month_earnings = 0.0
    month_bb_earnings = 0.0
    month_hands = 0
    
    # Stake breakdown
    stake_data = {}
    
    # Time series data for graph
    session_data = []  # List of {date, earnings, bb_earnings, stake}
    
    for post in user_posts:
        try:
            # Parse metrics
            metrics_list = json.loads(post.data_frame_results)
            if not metrics_list or not isinstance(metrics_list, list):
                continue
                
            metrics = metrics_list[0]
            
            # Extract session data
            hands = metrics.get('VPIP Info', {}).get('num_viable_hands', 0)
            earnings = float(metrics.get('Session Earnings', 0))
            bb_earnings = float(metrics.get('Session BB Earnings', 0))
            stake = post.stake
            
            # Normalize stake before tracking
            normalized_stake = normalize_stake(stake)
            
            # Update totals
            total_hands += hands
            total_earnings += earnings
            total_bb_earnings += bb_earnings
            
            # Update monthly totals
            if post.date_created >= current_month_start:
                month_hands += hands
                month_earnings += earnings
                month_bb_earnings += bb_earnings
            
            # Track by stake
            if normalized_stake not in stake_data:
                stake_data[normalized_stake] = {
                    'hands': 0,
                    'earnings': 0.0,
                    'bb_earnings': 0.0,
                    'sessions': 0,
                    'winning_sessions': 0
                }
            
            stake_data[normalized_stake]['hands'] += hands
            stake_data[normalized_stake]['earnings'] += earnings
            stake_data[normalized_stake]['bb_earnings'] += bb_earnings
            stake_data[normalized_stake]['sessions'] += 1
            if earnings > 0:
                stake_data[normalized_stake]['winning_sessions'] += 1
            
            # Add to session data for graph (use normalized stake)
            session_data.append({
                'date': post.date_created.isoformat(),
                'earnings': earnings,
                'bb_earnings': bb_earnings,
                'stake': normalized_stake
            })
            
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            continue
    
    # Process live sessions
    for session in live_sessions:
        try:
            # Convert EUR to USD for live sessions
            profit_loss_eur = session.profit_loss
            profit_loss_usd = profit_loss_eur * EUR_TO_USD_RATE
            
            # Get BB earnings (already calculated in EUR, convert to USD equivalent)
            bb_earnings = session.profit_loss_bb  # This is in BB, no conversion needed
            
            # Use stakes as the "stake" identifier, prefixed with "Live: "
            stake = f"Live: {session.stakes}"
            
            # Update totals
            total_earnings += profit_loss_usd
            total_bb_earnings += bb_earnings
            # Live sessions don't have hands, so we don't increment total_hands
            
            # Update monthly totals
            if session.session_date >= current_month_start:
                month_earnings += profit_loss_usd
                month_bb_earnings += bb_earnings
            
            # Track by stake
            if stake not in stake_data:
                stake_data[stake] = {
                    'hands': 0,  # Live sessions don't have hand counts
                    'earnings': 0.0,
                    'bb_earnings': 0.0,
                    'sessions': 0,
                    'winning_sessions': 0
                }
            
            stake_data[stake]['earnings'] += profit_loss_usd
            stake_data[stake]['bb_earnings'] += bb_earnings
            stake_data[stake]['sessions'] += 1
            if profit_loss_usd > 0:
                stake_data[stake]['winning_sessions'] += 1
            
            # Add to session data for graph
            session_data.append({
                'date': session.session_date.isoformat(),
                'earnings': profit_loss_usd,
                'bb_earnings': bb_earnings,
                'stake': stake,
                'type': 'live'  # Mark as live session
            })
            
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
    
    if total_hands == 0 and not live_sessions:
        return None
    
    # Calculate BB/100 and winrate for each stake
    for stake, data in stake_data.items():
        if data['hands'] > 0:
            # Only calculate BB/100 for online sessions (they have hands)
            data['bb_per_100'] = (data['bb_earnings'] / data['hands']) * 100
        else:
            # Live sessions don't have hands, so BB/100 is not applicable
            data['bb_per_100'] = None
        data['winrate'] = (data['winning_sessions'] / data['sessions'] * 100) if data['sessions'] > 0 else 0
    
    # Calculate overall BB/100
    overall_bb_per_100 = (total_bb_earnings / total_hands) * 100 if total_hands > 0 else 0
    
    # Calculate cumulative earnings for running bankroll
    cumulative_earnings = 0.0
    cumulative_bb = 0.0
    running_bankroll = []
    
    for session in session_data:
        cumulative_earnings += session['earnings']
        cumulative_bb += session['bb_earnings']
        running_bankroll.append({
            'date': session['date'],
            'bankroll': cumulative_earnings,
            'bankroll_bb': cumulative_bb
        })
    
    # Current bankroll is the cumulative total
    current_bankroll = cumulative_earnings
    
    return {
        'current_bankroll': current_bankroll,
        'current_bankroll_bb': cumulative_bb,
        'total_profit_loss': total_earnings,
        'total_profit_loss_bb': total_bb_earnings,
        'month_profit_loss': month_earnings,
        'month_profit_loss_bb': month_bb_earnings,
        'month_hands': month_hands,
        'total_hands': total_hands,
        'overall_bb_per_100': overall_bb_per_100,
        'stake_breakdown': stake_data,
        'session_data': session_data,
        'running_bankroll': running_bankroll
    }


@views.route('/view_analytics')
@login_required
def view_analytics():
    try:
        user_id = current_user.id

        stage = request.args.get('stage', 'math_learning')  # Default to 'math_learning'

        if stage == 'math_learning':
            # Fetch the latest 10 results, ordered by timestamp (newest first)
            quiz_results = QuantMathResult.query.filter_by(user_id=user_id).order_by(QuantMathResult.timestamp.desc()).limit(10).all()
            placeholder_date = datetime.datetime(1970, 1, 1)

            # Ensure there are 10 entries by filling missing ones with zeros
            while len(quiz_results) < 10:
                quiz_results.append(QuantMathResult(
                    user_id=user_id,
                    total_time=0.0,
                    mean_bayes_time=0.0,
                    mean_coupon_time=0.0,
                    mean_option_time=0.0,
                    mean_ev_time=0.0,
                    timestamp=placeholder_date
                ))

            return render_template('view_analytics.html', user=current_user, quiz_results=quiz_results)
        
        elif stage == 'bankroll':
            bankroll_data = calculate_bankroll_data(user_id)
            return render_template('view_analytics.html', user=current_user, bankroll_data=bankroll_data)
        
        elif stage == 'live_sessions':
            live_sessions = LiveSession.query.filter_by(user_id=user_id).order_by(LiveSession.session_date.desc()).all()
            
            # Calculate statistics
            total_profit_loss = sum(session.cash_out - session.buy_in for session in live_sessions)
            winning_sessions = sum(1 for session in live_sessions if session.cash_out > session.buy_in)
            win_rate = (winning_sessions / len(live_sessions) * 100) if live_sessions else 0
            avg_profit = total_profit_loss / len(live_sessions) if live_sessions else 0
            
            # Calculate BB statistics
            total_hours = sum(session.hours_played for session in live_sessions if session.hours_played)
            bb_per_hour_sessions = [session.bb_per_hour for session in live_sessions if session.bb_per_hour is not None]
            avg_bb_per_hour = sum(bb_per_hour_sessions) / len(bb_per_hour_sessions) if bb_per_hour_sessions else None
            
            # Calculate total profit/loss in BB
            total_profit_loss_bb = sum(session.profit_loss_bb for session in live_sessions if session.profit_loss_bb is not None)
            
            return render_template('view_analytics.html', 
                                 user=current_user, 
                                 live_sessions=live_sessions,
                                 total_profit_loss=total_profit_loss,
                                 total_profit_loss_bb=total_profit_loss_bb,
                                 win_rate=win_rate,
                                 avg_profit=avg_profit,
                                 avg_bb_per_hour=avg_bb_per_hour,
                                 total_hours=total_hours)
        
        return render_template('view_analytics.html', user=current_user)
    except Exception as e:
        print(f"Error in view_analytics: {e}")
        flash(f'Error loading analytics: {str(e)}', category='error')
        return redirect(url_for('views.view_analytics'))


@views.route('/save_quant_test', methods=['POST'])
@login_required
def save_quant_test():
    # Retrieve data from the JSON payload
    data = request.get_json()
    bayes_time = data.get('bayes_time')  # Accumulated time for Bayes Theorem questions
    coupon_time = data.get('coupon_time')  # Accumulated time for Coupon Collector questions
    option_time = data.get('option_time')  # Accumulated time for Options Pricing questions
    ev_time = data.get('ev_time')  # Accumulated time for Expected Value questions
    total_time = data.get('total_time')  # Total time for the entire quiz

    # Calculate the mean time for each category (rounded to 1 decimal place)
    mean_bayes_time = round(bayes_time / 3, 1) if bayes_time else 0
    mean_coupon_time = round(coupon_time / 3, 1) if coupon_time else 0
    mean_option_time = round(option_time / 3, 1) if option_time else 0
    mean_ev_time = round(ev_time / 3, 1) if ev_time else 0

    # Fetch existing results for the current user
    results = QuantMathResult.query.filter_by(user_id=current_user.id).order_by(QuantMathResult.timestamp.desc()).all()

    if len(results) >= 10:
        # If there are already 10 results, remove the oldest one
        db.session.delete(results[-1])

    # Create a new result entry
    new_result = QuantMathResult(
        user_id=current_user.id,
        total_time=total_time,
        mean_bayes_time=mean_bayes_time,
        mean_coupon_time=mean_coupon_time,
        mean_option_time=mean_option_time,
        mean_ev_time=mean_ev_time,
    )

    # Save the new result to the database
    db.session.add(new_result)
    db.session.commit()

    flash('Quant test results saved successfully!', category='success')
    return jsonify({'success': True}), 200



@views.route('/get_quant_questions', methods=['GET'])
@login_required
def get_quant_questions():
    questions = get_quantmath_questions()  # Get the questions from your existing generator
    return jsonify(questions)


def normalize_stake(stake):
    """Normalize stake string to handle variations like .25/.5 and .25/.50 (same stake)"""
    if not stake:
        return stake
    
    try:
        # Remove any whitespace
        stake = stake.strip()
        
        # Split by /
        parts = stake.split('/')
        if len(parts) != 2:
            return stake
        
        sb_str = parts[0].strip()
        bb_str = parts[1].strip()
        
        # Convert to floats (this handles .5, .50, 0.5, 0.50 all as 0.5)
        sb = float(sb_str)
        bb = float(bb_str)
        
        # Always format with 2 decimal places for consistency
        # This ensures .25/.5 becomes 0.25/0.50 and .25/.50 becomes 0.25/0.50
        normalized = f"{sb:.2f}/{bb:.2f}"
        
        # Remove leading zero if present for small decimals (optional, but cleaner)
        # e.g., "0.25/0.50" -> ".25/.50"
        if sb < 1 and bb < 1:
            normalized = normalized.replace("0.", ".")
        
        return normalized
    except (ValueError, AttributeError):
        # If parsing fails, return original
        return stake


def aggregate_user_stats(user_id, filters=None):
    """Aggregate poker statistics for a user across all their sessions (online and live)"""
    user_posts = Post.query.filter_by(author=user_id).all()
    live_sessions = LiveSession.query.filter_by(user_id=user_id).all()
    
    # Currency conversion rate (USD to EUR) - update this periodically or fetch from API
    USD_TO_EUR_RATE = 0.92  # Approximate current rate
    
    # If no posts and no live sessions, return empty stats
    if not user_posts and not live_sessions:
        return {
            'total_combined_earnings_eur': 0,
            'total_combined_bb': 0,
            'total_combined_sessions': 0,
            'online_sessions': 0,
            'online_total_hands': 0,
            'online_total_earnings': 0,
            'online_total_earnings_eur': 0,
            'online_total_bb_earnings': 0,
            'online_bb_per_100': 0,
            'online_avg_session_earnings': 0,
            'online_win_rate': 0,
            'live_sessions': 0,
            'live_total_earnings': 0,
            'live_total_bb_earnings': 0,
            'live_total_hours': 0,
            'live_avg_session_earnings': 0,
            'live_win_rate': 0,
            'live_avg_bb_per_hour': None,
            'stake_breakdown': {},
            'site_breakdown': {},
            'recent_sessions': [],
            'recent_live_sessions': [],
            'aggregated_board_analysis': {},
            'aggregated_hand_matrix': {},
            'aggregated_rfi_matrix': {},
            'aggregated_three_bet_matrix': {},
            'aggregated_four_bet_matrix': {},
            'aggregated_positional_matchups': {}
        }
    
    # Online (USD) statistics
    online_sessions = len(user_posts)
    online_total_hands = 0
    online_total_earnings = 0  # USD
    online_total_bb_earnings = 0
    online_session_earnings = []
    online_session_dates = []
    stake_breakdown = {}
    site_breakdown = {}
    
    # Live (EUR) statistics
    live_total_sessions = len(live_sessions)
    live_total_earnings = 0  # EUR
    live_total_bb_earnings = 0
    live_total_hours = 0
    live_session_earnings = []
    live_session_dates = []
    
    # Aggregated post metrics (BB-based) across all posts
    aggregated_post_metrics = {
        'total_hands': 0,
        'vpip_count': 0,
        'rfi_count': 0,
        'rfi_hands': 0,
        'three_bet_count': 0,
        'three_bet_opportunities': 0,
        'four_bet_count': 0,
        'four_bet_opportunities': 0,
        'iso_raise_count': 0,
        'iso_raise_hands': 0,
        'total_bb_earnings': 0.0
    }
    aggregated_postflop = {
        'flop': {
            'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0,
            'ip': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0},
            'oop': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0},
            'multiway': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0}
        },
        'turn': {
            'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0,
            'ip': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0},
            'oop': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0},
            'multiway': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0}
        },
        'river': {
            'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0,
            'ip': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0},
            'oop': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0},
            'multiway': {'total_hands': 0, 'bets': 0, 'checks': 0, 'calls': 0, 'folds': 0, 'raises': 0}
        }
    }
    
    # Apply optional filters to posts
    if filters:
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        stake_filter = filters.get('stake')
        site_filter = filters.get('site')
        filtered_posts = []
        for post in user_posts:
            if start_date and post.date_created < start_date:
                continue
            if end_date and post.date_created > end_date:
                continue
            if stake_filter and normalize_stake(post.stake) != stake_filter:
                continue
            if site_filter and post.category != site_filter:
                continue
            filtered_posts.append(post)
        user_posts = filtered_posts

    def load_post_metrics(post):
        if not post.data_frame_results:
            return None
        try:
            metrics_list = json.loads(post.data_frame_results)
        except Exception:
            return None
        if not metrics_list or not isinstance(metrics_list, list):
            return None
        metrics = metrics_list[0]
        if isinstance(metrics, str):
            try:
                metrics = json.loads(metrics)
            except Exception:
                try:
                    metrics = ast.literal_eval(metrics)
                except Exception:
                    return None
        return metrics if isinstance(metrics, dict) else None

    def parse_nested_metric(value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except Exception:
                try:
                    return ast.literal_eval(value)
                except Exception:
                    return {}
        return {}

    def update_action_agg(target, source):
        if not isinstance(source, dict):
            return
        target['total_hands'] += source.get('total_hands', 0)
        target['bets'] += source.get('bets', 0)
        target['checks'] += source.get('checks', 0)
        target['calls'] += source.get('calls', 0)
        target['folds'] += source.get('folds', 0)
        target['raises'] += source.get('raises', 0)
        for key in ['ip', 'oop', 'multiway']:
            src_bucket = source.get(key, {})
            if not isinstance(src_bucket, dict):
                continue
            target[key]['total_hands'] += src_bucket.get('total_hands', 0) or src_bucket.get('total', 0)
            target[key]['bets'] += src_bucket.get('bets', 0)
            target[key]['checks'] += src_bucket.get('checks', 0)
            target[key]['calls'] += src_bucket.get('calls', 0)
            target[key]['folds'] += src_bucket.get('folds', 0)
            target[key]['raises'] += src_bucket.get('raises', 0)

    for post in user_posts:
        try:
            metrics = load_post_metrics(post)
            if not metrics:
                continue

                # Extract key metrics
            vpip_info = parse_nested_metric(metrics.get('VPIP Info', {}))
            rfi_info = parse_nested_metric(metrics.get('RFI VPIP Info', {}))
            three_bet_info = parse_nested_metric(metrics.get('Three bet info', {}))
            four_bet_info = parse_nested_metric(metrics.get('Four bet info', {}))
            iso_raise_info = parse_nested_metric(metrics.get('Iso Raise info', {}))

            hands = vpip_info.get('num_viable_hands', 0)
            earnings = float(metrics.get('Session Earnings', 0))
            bb_earnings = float(metrics.get('Session BB Earnings', 0))
            
            online_total_hands += hands
            online_total_earnings += earnings
            online_total_bb_earnings += bb_earnings
            online_session_earnings.append(earnings)
            online_session_dates.append(post.date_created)
            
            aggregated_post_metrics['total_hands'] += hands or 0
            aggregated_post_metrics['vpip_count'] += vpip_info.get('vpip_count', 0) or 0
            aggregated_post_metrics['rfi_count'] += rfi_info.get('rfi_count', 0) or 0
            aggregated_post_metrics['rfi_hands'] += rfi_info.get('num_viable_hands', 0) or 0
            aggregated_post_metrics['three_bet_count'] += three_bet_info.get('Num_three_bets', 0) or 0
            aggregated_post_metrics['three_bet_opportunities'] += three_bet_info.get('hero_3bet_opportunities', 0) or 0
            aggregated_post_metrics['four_bet_count'] += four_bet_info.get('Num_four_bets', 0) or 0
            aggregated_post_metrics['four_bet_opportunities'] += four_bet_info.get('hero_4bet_opportunities', 0) or 0
            aggregated_post_metrics['iso_raise_count'] += iso_raise_info.get('Num_iso_raises', 0) or 0
            aggregated_post_metrics['iso_raise_hands'] += iso_raise_info.get('Viable_hands', 0) or 0
            aggregated_post_metrics['total_bb_earnings'] += bb_earnings or 0.0

            # Aggregate postflop action frequencies
            flop_freq = parse_nested_metric(metrics.get('Flop Action Frequency', {}))
            turn_freq = parse_nested_metric(metrics.get('Turn Action Frequency', {}))
            river_freq = parse_nested_metric(metrics.get('River Action Frequency', {}))
            update_action_agg(aggregated_postflop['flop'], flop_freq)
            update_action_agg(aggregated_postflop['turn'], turn_freq)
            update_action_agg(aggregated_postflop['river'], river_freq)
                
                # Track stake breakdown (normalize stake first)
            stake = normalize_stake(post.stake)
            if stake not in stake_breakdown:
                stake_breakdown[stake] = {'sessions': 0, 'earnings': 0, 'hands': 0}
            stake_breakdown[stake]['sessions'] += 1
            stake_breakdown[stake]['earnings'] += earnings
            stake_breakdown[stake]['hands'] += hands
            
            # Track site breakdown
            site = post.category
            if site not in site_breakdown:
                site_breakdown[site] = {'sessions': 0, 'earnings': 0, 'hands': 0}
            site_breakdown[site]['sessions'] += 1
            site_breakdown[site]['earnings'] += earnings
            site_breakdown[site]['hands'] += hands
                
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    
    # Process live sessions
    for session in live_sessions:
        profit_loss = session.profit_loss
        profit_loss_bb = session.profit_loss_bb
        
        live_total_earnings += profit_loss
        if profit_loss_bb is not None:
            live_total_bb_earnings += profit_loss_bb
        if session.hours_played:
            live_total_hours += session.hours_played
        
        live_session_earnings.append(profit_loss)
        live_session_dates.append(session.session_date)
    
    # Calculate combined totals (convert USD to EUR)
    total_online_earnings_eur = online_total_earnings * USD_TO_EUR_RATE
    total_combined_earnings_eur = total_online_earnings_eur + live_total_earnings
    total_combined_bb = online_total_bb_earnings + live_total_bb_earnings
    total_combined_sessions = online_sessions + live_total_sessions
    
    # Calculate derived statistics for online
    online_bb_per_100 = (online_total_bb_earnings / online_total_hands) * 100 if online_total_hands > 0 else 0
    online_avg_session_earnings = online_total_earnings / online_sessions if online_sessions > 0 else 0
    online_win_rate = len([e for e in online_session_earnings if e > 0]) / online_sessions * 100 if online_sessions > 0 else 0
    
    # Calculate derived statistics for live
    live_avg_session_earnings = live_total_earnings / live_total_sessions if live_total_sessions > 0 else 0
    live_win_rate = len([e for e in live_session_earnings if e > 0]) / live_total_sessions * 100 if live_total_sessions > 0 else 0
    live_avg_bb_per_hour = live_total_bb_earnings / live_total_hours if live_total_hours > 0 else None
    
    # Calculate best and worst sessions (online)
    best_online_session = max(online_session_earnings) if online_session_earnings else 0
    worst_online_session = min(online_session_earnings) if online_session_earnings else 0
    
    # Calculate best and worst sessions (live)
    best_live_session = max(live_session_earnings) if live_session_earnings else 0
    worst_live_session = min(live_session_earnings) if live_session_earnings else 0
    
    # Process recent sessions with earnings data (online)
    recent_sessions_with_earnings = []
    for post in user_posts[:5]:  # Last 5 online sessions
        session_earnings = 0
        hands = 0
        try:
            if post.data_frame_results:
                metrics_list = json.loads(post.data_frame_results)
                if metrics_list and isinstance(metrics_list, list):
                    metrics = metrics_list[0]

                    # Normalize metrics if stored as a JSON string
                    if isinstance(metrics, str):
                        try:
                            metrics = json.loads(metrics)
                        except json.JSONDecodeError:
                            continue
                    if not isinstance(metrics, dict):
                        continue

                    session_earnings = float(metrics.get('Session Earnings', 0))

                    vpip_info = metrics.get('VPIP Info', {})
                    if isinstance(vpip_info, str):
                        try:
                            vpip_info = json.loads(vpip_info)
                        except json.JSONDecodeError:
                            vpip_info = {}
                    if not isinstance(vpip_info, dict):
                        vpip_info = {}

                    hands = vpip_info.get('num_viable_hands', 0)
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            session_earnings = 0
            hands = 0
        
        recent_sessions_with_earnings.append({
            'post': post,
            'earnings': round(session_earnings, 2),
            'type': 'online',
            'stake': normalize_stake(post.stake),
            'date': post.date_created,
            'hands': hands
        })
    
    # Process recent live sessions
    recent_live_sessions = []
    for session in sorted(live_sessions, key=lambda x: x.session_date, reverse=True)[:5]:
        recent_live_sessions.append({
            'session': session,
            'earnings': round(session.profit_loss, 2),
            'type': 'live'
        })
    
    # Aggregate Board High Card Analysis
    aggregated_board_analysis = {}
    for post in user_posts:
        try:
            metrics = load_post_metrics(post)
            if not metrics:
                continue

            board_analysis = parse_nested_metric(metrics.get('Board High Card Analysis', {}))
            if not isinstance(board_analysis, dict):
                board_analysis = {}

            for board_type, data in board_analysis.items():
                if board_type not in aggregated_board_analysis:
                    aggregated_board_analysis[board_type] = {
                        'total_hands': 0,
                        'total_bb_earnings': 0.0,
                        'avg_bb_per_hand': 0.0
                    }
                aggregated_board_analysis[board_type]['total_hands'] += data.get('total_hands', 0)
                aggregated_board_analysis[board_type]['total_bb_earnings'] += data.get('total_bb_earnings', 0)
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    
    # Calculate averages for board analysis
    for board_type in aggregated_board_analysis:
        if aggregated_board_analysis[board_type]['total_hands'] > 0:
            aggregated_board_analysis[board_type]['avg_bb_per_hand'] = round(
                aggregated_board_analysis[board_type]['total_bb_earnings'] / 
                aggregated_board_analysis[board_type]['total_hands'], 
                2
            )
            aggregated_board_analysis[board_type]['total_bb_earnings'] = round(
                aggregated_board_analysis[board_type]['total_bb_earnings'], 2
            )
    
    # Sort board analysis by total BB earnings
    sorted_board_analysis = dict(sorted(
        aggregated_board_analysis.items(), 
        key=lambda x: x[1]['total_bb_earnings']
    ))
    
    # Aggregate Positional Matchups (split by pot type: RFI, 3-bet, 4-bet, and multiway)
    aggregated_positional_matchups = {
        'RFI Pots': {},
        '3-Bet Pots': {},
        '4-Bet Pots': {},
        'RFI Multiway Pots': {},
        '3-Bet Multiway Pots': {},
        '4-Bet Multiway Pots': {}
    }
    aggregated_matchup_debug = {
        'RFI Pots': {},
        '3-Bet Pots': {},
        '4-Bet Pots': {},
        'RFI Multiway Pots': {},
        '3-Bet Multiway Pots': {},
        '4-Bet Multiway Pots': {}
    }
    
    for post in user_posts:
        try:
            metrics = load_post_metrics(post)
            if not metrics:
                continue
            positional_matchups = parse_nested_metric(metrics.get('Positional Matchups', {}))
            
            # Handle both old format (flat dict) and new format (nested by pot type)
            if isinstance(positional_matchups, dict):
                # Check if it's the new format (has 'RFI Pots', '3-Bet Pots', etc.)
                if 'RFI Pots' in positional_matchups or '3-Bet Pots' in positional_matchups:
                    # New format - iterate through pot types (including multiway)
                    for pot_type in ['RFI Pots', '3-Bet Pots', '4-Bet Pots', 'RFI Multiway Pots', '3-Bet Multiway Pots', '4-Bet Multiway Pots']:
                        pot_matchups = positional_matchups.get(pot_type, {})
                        for matchup, data in pot_matchups.items():
                            if matchup not in aggregated_positional_matchups[pot_type]:
                                aggregated_positional_matchups[pot_type][matchup] = {
                                    'total_hands': 0,
                                    'total_bb_earnings': 0.0,
                                    'total_earnings': 0.0,
                                    'avg_bb_per_hand': 0.0
                                }
                            aggregated_positional_matchups[pot_type][matchup]['total_hands'] += data.get('total_hands', 0)
                            aggregated_positional_matchups[pot_type][matchup]['total_bb_earnings'] += data.get('total_bb_earnings', 0)
                            aggregated_positional_matchups[pot_type][matchup]['total_earnings'] += data.get('total_earnings', 0)
                            if matchup not in aggregated_matchup_debug[pot_type]:
                                aggregated_matchup_debug[pot_type][matchup] = []
                            if data.get('total_hands', 0):
                                aggregated_matchup_debug[pot_type][matchup].append({
                                    'post_id': post.id,
                                    'post_date': post.date_created.strftime('%Y-%m-%d'),
                                    'hand_id': data.get('hand_id') or data.get('hand_ids'),
                                    'hands': data.get('total_hands', 0),
                                    'bb': data.get('total_bb_earnings', 0),
                                    'earnings': data.get('total_earnings', 0)
                                })
                else:
                    # Old format - treat as RFI Pots for backward compatibility
                    for matchup, data in positional_matchups.items():
                        if matchup not in aggregated_positional_matchups['RFI Pots']:
                            aggregated_positional_matchups['RFI Pots'][matchup] = {
                                'total_hands': 0,
                                'total_bb_earnings': 0.0,
                                'total_earnings': 0.0,
                                'avg_bb_per_hand': 0.0
                            }
                        aggregated_positional_matchups['RFI Pots'][matchup]['total_hands'] += data.get('total_hands', 0)
                        aggregated_positional_matchups['RFI Pots'][matchup]['total_bb_earnings'] += data.get('total_bb_earnings', 0)
                        aggregated_positional_matchups['RFI Pots'][matchup]['total_earnings'] += data.get('total_earnings', 0)
                        if matchup not in aggregated_matchup_debug['RFI Pots']:
                            aggregated_matchup_debug['RFI Pots'][matchup] = []
                        if data.get('total_hands', 0):
                            aggregated_matchup_debug['RFI Pots'][matchup].append({
                                'post_id': post.id,
                                'post_date': post.date_created.strftime('%Y-%m-%d'),
                                'hand_id': data.get('hand_id') or data.get('hand_ids'),
                                'hands': data.get('total_hands', 0),
                                'bb': data.get('total_bb_earnings', 0),
                                'earnings': data.get('total_earnings', 0)
                            })
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    
    # Calculate averages and sort for each pot type
    sorted_positional_matchups = {}
    for pot_type in ['RFI Pots', '3-Bet Pots', '4-Bet Pots', 'RFI Multiway Pots', '3-Bet Multiway Pots', '4-Bet Multiway Pots']:
        for matchup in aggregated_positional_matchups[pot_type]:
            if aggregated_positional_matchups[pot_type][matchup]['total_hands'] > 0:
                aggregated_positional_matchups[pot_type][matchup]['avg_bb_per_hand'] = round(
                    aggregated_positional_matchups[pot_type][matchup]['total_bb_earnings'] / 
                    aggregated_positional_matchups[pot_type][matchup]['total_hands'], 
                    2
                )
                aggregated_positional_matchups[pot_type][matchup]['total_bb_earnings'] = round(
                    aggregated_positional_matchups[pot_type][matchup]['total_bb_earnings'], 2
                )
                aggregated_positional_matchups[pot_type][matchup]['total_earnings'] = round(
                    aggregated_positional_matchups[pot_type][matchup]['total_earnings'], 2
                )
        
        # Sort by total BB earnings
        sorted_positional_matchups[pot_type] = dict(sorted(
            aggregated_positional_matchups[pot_type].items(), 
            key=lambda x: x[1]['total_bb_earnings']
        ))
    
    # Aggregate Hand Matrix Analysis
    aggregated_hand_matrix = {}
    aggregated_rfi_matrix = {}
    aggregated_three_bet_matrix = {}
    aggregated_four_bet_matrix = {}
    for post in user_posts:
        try:
            metrics = load_post_metrics(post)
            if not metrics:
                continue

            def normalize_matrix(value):
                value = parse_nested_metric(value)
                return value if isinstance(value, dict) else {}

            def normalize_entry(value):
                value = parse_nested_metric(value)
                return value if isinstance(value, dict) else {}

            hand_matrix = normalize_matrix(metrics.get('Hand Matrix Analysis', {}))
            rfi_matrix = normalize_matrix(metrics.get('RFI Matrix Analysis', {}))
            three_bet_matrix = normalize_matrix(metrics.get('3-Bet Matrix Analysis', {}))
            four_bet_matrix = normalize_matrix(metrics.get('4-Bet Matrix Analysis', {}))
            
            # Aggregate BB earnings hand matrix
            for hand_type, hand_data in hand_matrix.items():
                hand_data = normalize_entry(hand_data)
                if hand_type not in aggregated_hand_matrix:
                    aggregated_hand_matrix[hand_type] = {
                        'total_hands': 0,
                        'total_bb_earnings': 0.0,
                        'avg_bb_per_hand': 0.0,
                        'combos': {}
                    }
                
                aggregated_hand_matrix[hand_type]['total_hands'] += hand_data.get('total_hands', 0)
                aggregated_hand_matrix[hand_type]['total_bb_earnings'] += hand_data.get('total_bb_earnings', 0)
                
                # Aggregate combos
                combos = normalize_entry(hand_data.get('combos', {}))
                for combo, combo_data in combos.items():
                    combo_data = normalize_entry(combo_data)
                    if combo not in aggregated_hand_matrix[hand_type]['combos']:
                        aggregated_hand_matrix[hand_type]['combos'][combo] = {
                            'total_hands': 0,
                            'total_bb_earnings': 0.0,
                            'avg_bb_per_hand': 0.0
                        }
                    aggregated_hand_matrix[hand_type]['combos'][combo]['total_hands'] += combo_data.get('total_hands', 0)
                    aggregated_hand_matrix[hand_type]['combos'][combo]['total_bb_earnings'] += combo_data.get('total_bb_earnings', 0)
            
            # Aggregate RFI matrix
            for hand_type, hand_data in rfi_matrix.items():
                hand_data = normalize_entry(hand_data)
                if hand_type not in aggregated_rfi_matrix:
                    aggregated_rfi_matrix[hand_type] = {
                        'total_rfi': 0,
                        'combos': {}
                    }
                
                aggregated_rfi_matrix[hand_type]['total_rfi'] += hand_data.get('total_rfi', 0)
                
                # Aggregate combos
                combos = normalize_entry(hand_data.get('combos', {}))
                for combo, combo_data in combos.items():
                    combo_data = normalize_entry(combo_data)
                    if combo not in aggregated_rfi_matrix[hand_type]['combos']:
                        aggregated_rfi_matrix[hand_type]['combos'][combo] = {
                            'total_rfi': 0
                        }
                    aggregated_rfi_matrix[hand_type]['combos'][combo]['total_rfi'] += combo_data.get('total_rfi', 0)
            
            # Aggregate 3-bet matrix
            for hand_type, hand_data in three_bet_matrix.items():
                hand_data = normalize_entry(hand_data)
                if hand_type not in aggregated_three_bet_matrix:
                    aggregated_three_bet_matrix[hand_type] = {
                        'total_three_bet': 0,
                        'combos': {}
                    }
                
                aggregated_three_bet_matrix[hand_type]['total_three_bet'] += hand_data.get('total_three_bet', 0)
                
                # Aggregate combos
                combos = normalize_entry(hand_data.get('combos', {}))
                for combo, combo_data in combos.items():
                    combo_data = normalize_entry(combo_data)
                    if combo not in aggregated_three_bet_matrix[hand_type]['combos']:
                        aggregated_three_bet_matrix[hand_type]['combos'][combo] = {
                            'total_three_bet': 0
                        }
                    aggregated_three_bet_matrix[hand_type]['combos'][combo]['total_three_bet'] += combo_data.get('total_three_bet', 0)
            
            # Aggregate 4-bet matrix
            for hand_type, hand_data in four_bet_matrix.items():
                hand_data = normalize_entry(hand_data)
                if hand_type not in aggregated_four_bet_matrix:
                    aggregated_four_bet_matrix[hand_type] = {
                        'total_four_bet': 0,
                        'combos': {}
                    }
                
                aggregated_four_bet_matrix[hand_type]['total_four_bet'] += hand_data.get('total_four_bet', 0)
                
                # Aggregate combos
                combos = normalize_entry(hand_data.get('combos', {}))
                for combo, combo_data in combos.items():
                    combo_data = normalize_entry(combo_data)
                    if combo not in aggregated_four_bet_matrix[hand_type]['combos']:
                        aggregated_four_bet_matrix[hand_type]['combos'][combo] = {
                            'total_four_bet': 0
                        }
                    aggregated_four_bet_matrix[hand_type]['combos'][combo]['total_four_bet'] += combo_data.get('total_four_bet', 0)
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    
    # Aggregate Leak Detection
    aggregated_leaks = []
    leak_impact_map = {}  # Track leaks by type and title to avoid duplicates
    
    for post in user_posts:
        try:
            metrics = load_post_metrics(post)
            if not metrics:
                continue

            leaks = metrics.get('Leak Detection', [])
            if isinstance(leaks, str):
                try:
                    leaks = json.loads(leaks)
                except json.JSONDecodeError:
                    try:
                        leaks = ast.literal_eval(leaks)
                    except Exception:
                        leaks = []
            if not isinstance(leaks, list):
                leaks = []

                for leak in leaks:
                    if isinstance(leak, str):
                        try:
                            leak = json.loads(leak)
                        except json.JSONDecodeError:
                            continue
                    if not isinstance(leak, dict):
                        continue

                    leak_key = f"{leak.get('type', 'unknown')}_{leak.get('title', 'unknown')}"
                    if leak_key not in leak_impact_map:
                        leak_impact_map[leak_key] = {
                            'type': leak.get('type', ''),
                            'title': leak.get('title', ''),
                            'severity': leak.get('severity', 'medium'),
                            'description': leak.get('description', ''),
                            'suggestion': leak.get('suggestion', ''),
                            'total_impact': 0.0,
                            'total_hands': 0,
                            'occurrences': 0,
                            'bb_per_100': 0.0,
                            'actual_freq': leak.get('actual_freq'),
                            'optimal_freq': leak.get('optimal_freq'),
                            'call_rate': leak.get('call_rate')
                        }
                    
                    # Aggregate the leak data
                    leak_impact_map[leak_key]['total_impact'] += leak.get('impact', 0)
                    leak_impact_map[leak_key]['total_hands'] += leak.get('hands', 0)
                    leak_impact_map[leak_key]['occurrences'] += 1
                    if leak.get('bb_per_100'):
                        # Average BB/100 across occurrences
                        current_bb = leak_impact_map[leak_key]['bb_per_100']
                        occurrences = leak_impact_map[leak_key]['occurrences']
                        leak_impact_map[leak_key]['bb_per_100'] = ((current_bb * (occurrences - 1)) + leak.get('bb_per_100', 0)) / occurrences
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    
    # Convert aggregated leaks to list and sort by impact
    for leak_data in leak_impact_map.values():
        aggregated_leaks.append({
            'type': leak_data['type'],
            'title': leak_data['title'],
            'severity': leak_data['severity'],
            'description': leak_data['description'],
            'suggestion': leak_data['suggestion'],
            'impact': round(leak_data['total_impact'] / leak_data['occurrences'], 1) if leak_data['occurrences'] > 0 else leak_data['total_impact'],
            'hands': leak_data['total_hands'],
            'occurrences': leak_data['occurrences'],
            'bb_per_100': round(leak_data['bb_per_100'], 2),
            'actual_freq': leak_data.get('actual_freq'),
            'optimal_freq': leak_data.get('optimal_freq'),
            'call_rate': leak_data.get('call_rate')
        })
    
    aggregated_leaks.sort(key=lambda x: x.get('impact', 0), reverse=True)
    
    # Calculate averages for hand matrix
    for hand_type in aggregated_hand_matrix:
        if aggregated_hand_matrix[hand_type]['total_hands'] > 0:
            aggregated_hand_matrix[hand_type]['avg_bb_per_hand'] = round(
                aggregated_hand_matrix[hand_type]['total_bb_earnings'] / 
                aggregated_hand_matrix[hand_type]['total_hands'], 
                2
            )
            aggregated_hand_matrix[hand_type]['total_bb_earnings'] = round(
                aggregated_hand_matrix[hand_type]['total_bb_earnings'], 2
            )
        
        # Calculate combo averages
        for combo in aggregated_hand_matrix[hand_type]['combos']:
            combo_data = aggregated_hand_matrix[hand_type]['combos'][combo]
            if combo_data['total_hands'] > 0:
                combo_data['avg_bb_per_hand'] = round(
                    combo_data['total_bb_earnings'] / combo_data['total_hands'], 
                    2
                )
                combo_data['total_bb_earnings'] = round(combo_data['total_bb_earnings'], 2)
    
    # Aggregate rates across all posts (BB-based)
    total_hands_all = aggregated_post_metrics['total_hands']
    vpip_rate = (aggregated_post_metrics['vpip_count'] / total_hands_all * 100) if total_hands_all > 0 else 0
    rfi_rate = (aggregated_post_metrics['rfi_count'] / aggregated_post_metrics['rfi_hands'] * 100) if aggregated_post_metrics['rfi_hands'] > 0 else 0
    three_bet_rate = (aggregated_post_metrics['three_bet_count'] / aggregated_post_metrics['three_bet_opportunities'] * 100) if aggregated_post_metrics['three_bet_opportunities'] > 0 else 0
    four_bet_rate = (aggregated_post_metrics['four_bet_count'] / aggregated_post_metrics['four_bet_opportunities'] * 100) if aggregated_post_metrics['four_bet_opportunities'] > 0 else 0
    iso_raise_rate = (aggregated_post_metrics['iso_raise_count'] / aggregated_post_metrics['iso_raise_hands'] * 100) if aggregated_post_metrics['iso_raise_hands'] > 0 else 0
    
    def finalize_action_bucket(bucket):
        total = bucket.get('total_hands', 0)
        bucket['bet_pct'] = round((bucket.get('bets', 0) / total * 100), 1) if total > 0 else 0
        bucket['check_pct'] = round((bucket.get('checks', 0) / total * 100), 1) if total > 0 else 0
        return bucket
    
    def finalize_action_stats(action_stats):
        finalize_action_bucket(action_stats)
        for key in ['ip', 'oop', 'multiway']:
            finalize_action_bucket(action_stats[key])
        return action_stats
    
    aggregated_postflop['flop'] = finalize_action_stats(aggregated_postflop['flop'])
    aggregated_postflop['turn'] = finalize_action_stats(aggregated_postflop['turn'])
    aggregated_postflop['river'] = finalize_action_stats(aggregated_postflop['river'])
    
    return {
        # Combined totals (in EUR)
        'total_combined_earnings_eur': round(total_combined_earnings_eur, 2),
        'total_combined_bb': round(total_combined_bb, 2),
        'total_combined_sessions': total_combined_sessions,
        
        # Online (USD) statistics
        'online_sessions': online_sessions,
        'online_total_hands': online_total_hands,
        'online_total_earnings': round(online_total_earnings, 2),  # USD
        'online_total_earnings_eur': round(total_online_earnings_eur, 2),  # Converted to EUR
        'online_total_bb_earnings': round(online_total_bb_earnings, 2),
        'online_bb_per_100': round(online_bb_per_100, 2),
        'online_avg_session_earnings': round(online_avg_session_earnings, 2),
        'online_win_rate': round(online_win_rate, 1),
        'online_best_session': round(best_online_session, 2),
        'online_worst_session': round(worst_online_session, 2),
        
        # Live (EUR) statistics
        'live_sessions': live_total_sessions,
        'live_total_earnings': round(live_total_earnings, 2),  # EUR
        'live_total_bb_earnings': round(live_total_bb_earnings, 2),
        'live_total_hours': round(live_total_hours, 1),
        'live_avg_session_earnings': round(live_avg_session_earnings, 2),
        'live_win_rate': round(live_win_rate, 1),
        'live_avg_bb_per_hour': round(live_avg_bb_per_hour, 2) if live_avg_bb_per_hour is not None else None,
        'live_best_session': round(best_live_session, 2),
        'live_worst_session': round(worst_live_session, 2),
        
        # Legacy fields (for backward compatibility - online stats)
        'total_sessions': online_sessions,
        'total_hands': online_total_hands,
        'total_earnings': round(online_total_earnings, 2),
        'total_bb_earnings': round(online_total_bb_earnings, 2),
        'bb_per_100': round(online_bb_per_100, 2),
        'avg_session_earnings': round(online_avg_session_earnings, 2),
        'win_rate': round(online_win_rate, 1),
        'best_session': round(best_online_session, 2),
        'worst_session': round(worst_online_session, 2),
        
        'stake_breakdown': stake_breakdown,
        'site_breakdown': site_breakdown,
        'session_earnings': online_session_earnings,
        'session_dates': online_session_dates,
        'formatted_session_dates': [d.strftime('%Y-%m-%d') for d in online_session_dates],
        'recent_sessions': recent_sessions_with_earnings,
        'recent_live_sessions': recent_live_sessions,
        'aggregated_board_analysis': sorted_board_analysis,
        'aggregated_hand_matrix': aggregated_hand_matrix,
        'aggregated_rfi_matrix': aggregated_rfi_matrix,
        'aggregated_three_bet_matrix': aggregated_three_bet_matrix,
        'aggregated_four_bet_matrix': aggregated_four_bet_matrix,
        'aggregated_positional_matchups': sorted_positional_matchups,
        'aggregated_leaks': aggregated_leaks,
        'usd_to_eur_rate': USD_TO_EUR_RATE,
        
        # Aggregated post metrics (BB-based)
        'agg_total_hands': aggregated_post_metrics['total_hands'],
        'agg_total_bb_earnings': round(aggregated_post_metrics['total_bb_earnings'], 2),
        'agg_vpip_count': aggregated_post_metrics['vpip_count'],
        'agg_vpip_rate': round(vpip_rate, 2),
        'agg_rfi_count': aggregated_post_metrics['rfi_count'],
        'agg_rfi_rate': round(rfi_rate, 2),
        'agg_three_bet_count': aggregated_post_metrics['three_bet_count'],
        'agg_three_bet_opportunities': aggregated_post_metrics['three_bet_opportunities'],
        'agg_three_bet_rate': round(three_bet_rate, 2),
        'agg_four_bet_count': aggregated_post_metrics['four_bet_count'],
        'agg_four_bet_opportunities': aggregated_post_metrics['four_bet_opportunities'],
        'agg_four_bet_rate': round(four_bet_rate, 2),
        'agg_iso_raise_count': aggregated_post_metrics['iso_raise_count'],
        'agg_iso_raise_rate': round(iso_raise_rate, 2),
        'agg_postflop_action': aggregated_postflop,
        'aggregated_matchup_debug': aggregated_matchup_debug
    }


@views.route('/user/<username>')
@login_required
def user_profile(username):
    """Display comprehensive user profile with aggregated statistics"""
    user = User.query.filter_by(username=username).first()
    
    if not user:
        flash('User not found.', category='error')
        return redirect(url_for('views.all_posts'))
    
    # Parse filters
    from datetime import datetime, timedelta
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    stake_filter = request.args.get('stake') or None
    site_filter = request.args.get('site') or None
    start_date = None
    end_date = None
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        start_date = None
        end_date = None
    
    filters = {
        'start_date': start_date,
        'end_date': end_date,
        'stake': normalize_stake(stake_filter) if stake_filter else None,
        'site': site_filter
    }
    
    # Filter options
    all_posts = Post.query.filter_by(author=user.id).all()
    stake_options = sorted({normalize_stake(p.stake) for p in all_posts if p.stake})
    site_options = sorted({p.category for p in all_posts if p.category})
    
    # Get aggregated statistics
    stats = aggregate_user_stats(user.id, filters=filters)
    
    return render_template('user_profile.html', 
                         user=current_user,
                         profile_user=user, 
                         stats=stats, 
                         current_user=current_user,
                         filters=filters,
                         filter_values={
                             'start_date': start_date_str or '',
                             'end_date': end_date_str or '',
                             'stake': stake_filter or '',
                             'site': site_filter or ''
                         },
                         filter_options={
                             'stakes': stake_options,
                             'sites': site_options
                         })


@views.route('/my-profile')
@login_required
def my_profile():
    """Redirect to current user's profile"""
    return redirect(url_for('views.user_profile', username=current_user.username))


@views.route('/dashboard')
@login_required
def dashboard():
    """Professional interactive dashboard with widgets, heat maps, and analytics"""
    stats = aggregate_user_stats(current_user.id)
    return render_template('dashboard.html', user=current_user, stats=stats)


@views.route('/add-live-session', methods=['POST'])
@login_required
def add_live_session():
    """Add a new live poker session"""
    try:
        from datetime import datetime
        
        session_date = datetime.strptime(request.form.get('session_date'), '%Y-%m-%d')
        location = request.form.get('location', '').strip()
        game_type = request.form.get('game_type')  # 'cash' or 'tournament'
        table_size = request.form.get('table_size', '').strip() or None
        game_name = request.form.get('game_name', '').strip() or None
        stakes = request.form.get('stakes', '').strip()
        buy_in = float(request.form.get('buy_in', 0))
        cash_out = float(request.form.get('cash_out', 0))
        currency = 'EUR'  # Live sessions always use EUR
        hours_played = request.form.get('hours_played')
        hours_played = float(hours_played) if hours_played else None
        notes = request.form.get('notes', '').strip()
        
        if not stakes:
            flash('Stakes are required', category='error')
            return redirect(url_for('views.view_analytics', stage='live_sessions'))
        
        new_session = LiveSession(
            user_id=current_user.id,
            session_date=session_date,
            location=location if location else None,
            game_type=game_type,
            table_size=table_size,
            game_name=game_name,
            stakes=stakes,
            buy_in=buy_in,
            cash_out=cash_out,
            currency=currency,
            hours_played=hours_played,
            notes=notes if notes else None
        )
        
        db.session.add(new_session)
        db.session.commit()
        
        flash('Live session added successfully!', category='success')
        return redirect(url_for('views.view_analytics', stage='live_sessions'))
        
    except ValueError as e:
        flash(f'Invalid input: {str(e)}', category='error')
        return redirect(url_for('views.view_analytics', stage='live_sessions'))
    except Exception as e:
        flash(f'Error adding session: {str(e)}', category='error')
        return redirect(url_for('views.view_analytics', stage='live_sessions'))


@views.route('/edit-live-session/<int:session_id>', methods=['POST'])
@login_required
def edit_live_session(session_id):
    """Edit an existing live poker session"""
    try:
        from datetime import datetime
        
        session = LiveSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        
        if not session:
            flash('Session not found or you do not have permission to edit it.', category='error')
            return redirect(url_for('views.view_analytics', stage='live_sessions'))
        
        session.session_date = datetime.strptime(request.form.get('session_date'), '%Y-%m-%d')
        session.location = request.form.get('location', '').strip() or None
        session.game_type = request.form.get('game_type')
        session.table_size = request.form.get('table_size', '').strip() or None
        session.game_name = request.form.get('game_name', '').strip() or None
        session.stakes = request.form.get('stakes', '').strip()
        session.buy_in = float(request.form.get('buy_in', 0))
        session.cash_out = float(request.form.get('cash_out', 0))
        session.currency = 'EUR'  # Live sessions always use EUR
        hours_played = request.form.get('hours_played')
        session.hours_played = float(hours_played) if hours_played else None
        session.notes = request.form.get('notes', '').strip() or None
        
        db.session.commit()
        
        flash('Session updated successfully!', category='success')
        return redirect(url_for('views.view_analytics', stage='live_sessions'))
        
    except ValueError as e:
        flash(f'Invalid input: {str(e)}', category='error')
        return redirect(url_for('views.view_analytics', stage='live_sessions'))
    except Exception as e:
        flash(f'Error updating session: {str(e)}', category='error')
        return redirect(url_for('views.view_analytics', stage='live_sessions'))


@views.route('/delete-live-session/<int:session_id>')
@login_required
def delete_live_session(session_id):
    """Delete a live poker session"""
    session = LiveSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    
    if not session:
        flash('Session not found or you do not have permission to delete it.', category='error')
    else:
        db.session.delete(session)
        db.session.commit()
        flash('Session deleted successfully!', category='success')
    
    return redirect(url_for('views.view_analytics', stage='live_sessions'))


@views.route('/get-live-session/<int:session_id>')
@login_required
def get_live_session(session_id):
    """Get live session data as JSON for editing"""
    session = LiveSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify({
        'session_date': session.session_date.strftime('%Y-%m-%d'),
        'location': session.location or '',
        'game_type': session.game_type or 'cash',
        'table_size': session.table_size or '',
        'game_name': session.game_name or '',
        'stakes': session.stakes,
        'buy_in': session.buy_in,
        'cash_out': session.cash_out,
        'currency': session.currency or 'USD',
        'hours_played': session.hours_played or '',
        'notes': session.notes or ''
    })
