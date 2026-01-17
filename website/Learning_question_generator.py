# This file creates practice questions and answers for learning pages.
# It builds the content the site shows when users study or quiz themselves.
# In short: it generates learning content for the website.
import random
import math

# Templates for generating questions
templates = {
    "coupon_collector": {
        "template_1": "A _x_ sided die is rolled until all the numbers show up at least _y_ times. What is the expected number of die rolls?",
        "template_2": "There are _x_ different coupons. You draw for them one at a time. How many are you expected to draw until you have _y_ of each token?",
        "template_3": "You are drawing cards from a standard 52 card deck. How many cards do you expect to draw till you have _y_ aces?"
    },
    "Bayes_Therem": {
        "template_1": "A jar with 20 coins has _x1_ fair coins, _x2_ coins with a _y1_ probability of heads, and _x3_ coins with a _y2_ probability of heads. Given a coin is removed and flipped _n_ times with the results _flips_, what is the probability it was a fair coin?",
        "template_2": "Assume the probability of having tuberculosis (TB) is _x1_, and a test for TB is _y1_% accurate. What is the probability one has TB if one tests positive for the disease?",
        "template_3": "Two manufacturers supply blankets to emergency relief organizations. Manufacturer A supplies _x1_ blankets and _y1_% are irregular in workmanship. Manufacturer B supplies _x2_ blankets and _y2_% are found to be irregular. Given that a blanket is irregular, find the probability that it came from manufacturer B."
    },
    "Options": {
        "template_1": "You are considering buying a European call option on a stock currently trading at _x1_ dollars. The option has a strike price of _x2_ dollars and expires in one year. The stock has a _y1_% chance of going up to _x3_ dollars and a _y2_% chance of going down to _x4_ dollars by the expiration date. What is the expected value of the option's payoff?",
        "template_2": "You have a portfolio consisting of 1 European call option and 1 European put option on the same stock with the same strike price of _x1_ dollars, and both options expire in one year. The stock price has a _y1_% chance of being _x2_ dollars, a _y2_% chance of being _x3_ dollars, and a _y3_% chance of being _x4_ dollars at expiration. What is the expected value of your portfolio's payoff?",
        "template_3": "A plot of land is being surveyed for oil, it will be values at 90$ per barrel of oil and regardless of oil it is worth 400,000$, it has an _x1_% and _x2_% chance of containing _y1_ or _y2_ barrels and an _x3_% probability of no oil, what is the value of the land"
    },
    "Expected_Value": {
        "template_1": "There are _x1_ blue balls, _x2_ red balls, and _x3_ green balls in a box. You guess the color of the ball before drawing, and you receive _y1_ dollars if you are correct. What is the dollar amount you would pay to play this game?",
        "template_2": "There are _x1_ balls, _x2_ red, and _x3_ black. What is the probability that a random ordering of the _x4_ balls does not have 2 black balls next to each other?",
        "template_3": "An unfair coin with a _x1_% chance of landing heads is flipped _x2_ times. If it lands _x2_ heads, you win €_y1_. If it lands in the sequence _s1_ or _s2_, you win €_y2_. What is the expected value of this game?"
    }
}

def get_quantmath_questions():
    generator = generate_quant_questions(templates)
    questions = generator.questions
    # Debugging: print out the structure of the questions dictionary
    print(questions)
    return questions


class generate_quant_questions():
    def __init__(self, templates):
        self.templates = templates
        self.questions = {"Bayes": self.generate_bayes_questions(), "EV": self.generate_ev_questions(), "Options": self.generate_options_questions(), "CouponCollector":self.generate_coupon_collector_questions()}

    def coupon_answer(self, n, y):
        """Coupon collector's problem with simplified expected value calculation."""
        x = sum(n * y / (n * y - i) for i in range(n * y))
        return x

    def generate_coupon_collector_questions(self):
        questions_and_answers = {}
        # Load the templates from JSON
        template_1 = self.templates["coupon_collector"]["template_1"]
        template_2 = self.templates["coupon_collector"]["template_2"]
        template_3 = self.templates["coupon_collector"]["template_3"]
        # Template 1: Die rolling example (with replacement)
        number_sides = random.randint(4, 8)
        number_shows = random.randint(1, 2)
        question_1 = template_1.replace("_x_", str(number_sides)).replace("_y_", str(number_shows))
        answer_1 = round(self.coupon_answer(number_sides, number_shows), 1)
        questions_and_answers[answer_1] = question_1
        # Template 2: Coupon drawing example (with replacement)
        number_coupons = random.randint(3, 10)
        number_of_each_coupon = random.randint(1, 2)
        question_2 = template_2.replace("_x_", str(number_coupons)).replace("_y_", str(number_of_each_coupon))
        answer_2 = round(self.coupon_answer(number_coupons, number_of_each_coupon), 1)
        questions_and_answers[answer_2] = question_2
        # Template 3: Card drawing example (without replacement)
        y = random.randint(1, 4)
        question_3 = template_3.replace("_y_", str(y))
        answer_3 = round(y*(53/5), 1)
        questions_and_answers[answer_3] = question_3
        return questions_and_answers

    def bayes_answer(self, pA, pB_given_A, pB):
        """Calculate P(A|B) using Bayes' Theorem."""
        return round((pB_given_A * pA) / pB, 2)

    def generate_random_flips(self, n):
        """Generate a random sequence of Heads (H) and Tails (T) of length n."""
        return ''.join(random.choice(['H', 'T']) for _ in range(n))

    def generate_bayes_questions(self):
        questions_and_answers = {}

        # Template 1: Coin flip problem
        x1 = random.randint(5, 10)
        x2 = random.randint(1, 5)
        x3 = 20 - x1 - x2
        y1 = round(random.uniform(0.4, 0.6), 1)
        y2 = round(random.uniform(0.1, 0.3), 1)
        n = random.randint(3, 5)  # Number of coin tosses
        flips = self.generate_random_flips(n)
        pA = x1 / 20  # Probability of picking a fair coin
        pB_given_A = 0.5 ** n  # Fair coin gives equal probability for any sequence
        pB = pB_given_A * pA + (y1 ** flips.count('H') * (1 - y1) ** flips.count('T')) * (x2 / 20) + (y2 ** flips.count('H') * (1 - y2) ** flips.count('T')) * (x3 / 20)
        question_1 = self.templates["Bayes_Therem"]["template_1"].replace("_x1_", str(x1)).replace("_x2_", str(x2)).replace("_x3_", str(x3)).replace("_y1_", str(y1)).replace("_y2_", str(y2)).replace("_n_", str(n)).replace("_flips_", flips)
        answer_1 = round(self.bayes_answer(pA, pB_given_A, pB), 2)
        questions_and_answers[answer_1] = question_1

        # Template 2: Tuberculosis test problem
        x1 = round(random.uniform(0.01, 0.1), 2)  # Random probability of having tuberculosis
        y1 = round(random.uniform(0.90, 0.99), 2)  # Random accuracy of TB test
        p_TB = x1
        p_not_TB = 1 - p_TB
        p_pos_given_TB = y1
        p_pos_given_not_TB = round(1 - y1, 5)
        p_pos = (p_pos_given_TB * p_TB) + (p_pos_given_not_TB * p_not_TB)
        question_2 = self.templates["Bayes_Therem"]["template_2"].replace("_x1_", str(x1)).replace("_y1_", str(y1 * 100))
        answer_2 = round(self.bayes_answer(p_TB, p_pos_given_TB, p_pos), 2)
        questions_and_answers[answer_2] = question_2

        # Template 3: Blanket manufacturer problem
        x1 = random.choice([1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000])  # Random number of blankets from Manufacturer A
        x2 = random.choice([1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 2600, 2800, 3000])  # Random number of blankets from Manufacturer B
        y1 = random.randint(1, 12)  # Random percentage irregular for Manufacturer A
        y2 = random.randint(1, 12)  # Random percentage irregular for Manufacturer B
        num_A = x1
        num_B = x2
        p_irregular_given_A = y1 / 100
        p_irregular_given_B = y2 / 100
        p_irregular = (p_irregular_given_A * (num_A / (num_A + num_B))) + (p_irregular_given_B * (num_B / (num_A + num_B)))
        question_3 = self.templates["Bayes_Therem"]["template_3"].replace("_x1_", str(x1)).replace("_y1_", str(y1)).replace("_x2_", str(x2)).replace("_y2_", str(y2))
        answer_3 = round(self.bayes_answer(num_B / (num_A + num_B), p_irregular_given_B, p_irregular), 2)
        questions_and_answers[answer_3] = question_3

        return questions_and_answers

    def generate_options_questions(self):
        questions_and_answers = {}

        # Template 1: Simple Expected Value of a Call Option
        x1 = random.randint(90, 110)  # Current stock price
        x2 = random.randint(95, 115)  # Strike price
        y1 = random.randint(30, 70)  # Chance of price increase in percentage
        y2 = 100 - y1  # Chance of price decrease in percentage
        x3 = random.randint(110, 130)  # Price after increase
        x4 = random.randint(70, 90)  # Price after decrease
        EV_call = (y1 / 100) * max(x3 - x2, 0) + (y2 / 100) * max(x4 - x2, 0)
        question_1 = self.templates["Options"]["template_1"].replace("_x1_", str(x1)).replace("_x2_", str(x2)).replace("_y1_", str(y1)).replace("_x3_", str(x3)).replace("_y2_", str(y2)).replace("_x4_", str(x4))
        questions_and_answers[round(EV_call, 2)] = question_1

        # Template 2: Expected Value of a Straddle
        x1 = random.randint(90, 110)  # Strike price
        y1 = random.randint(20, 50)  # Chance of $x2 price
        y2 = random.randint(20, 50)  # Chance of $x3 price
        y3 = 100 - y1 - y2  # Chance of $x4 price
        x2 = random.randint(60, 80)  # Stock price scenario 1
        x3 = random.randint(80, 89)  # Stock price scenario 2
        x4 = random.randint(110, 130)  # Stock price scenario 3
        EV_straddle = (y1*(x1-x2) + y2*(x1-x3) + y3*(x4-x1))/100
        question_2 = self.templates["Options"]["template_2"].replace("_x1_", str(x1)).replace("_y1_", str(y1)).replace("_x2_", str(x2)).replace("_y2_", str(y2)).replace("_x3_", str(x3)).replace("_y3_", str(y3)).replace("_x4_", str(x4))
        questions_and_answers[round(EV_straddle, 2)] = question_2


        # oil land
        x1 = round(random.uniform(0.3, 0.5), 2)  # Probability of y1 barrels (30% to 50%)
        x2 = round(random.uniform(0.3, 0.5), 2)  # Probability of y2 barrels (30% to 50%)
        x3 = round(1 - (x1 + x2), 2)  # Probability of no oil (remaining probability)
        y1 = random.randint(5000, 10000)  # Number of barrels in outcome x1
        y2 = random.randint(1000, 5000)  # Number of barrels in outcome x2
        # Calculate the expected value of the land
        expected_value = self.calculate_land_value(x1, x2, x3, y1, y2)

        # Generate the question using the template
        question_3 = self.templates["Options"]["template_3"].replace("_x1_", str(x1 * 100)).replace("_x2_",
                                                                                                         str(x2 * 100)).replace(
            "_y1_", str(y1)).replace("_y2_", str(y2)).replace("_x3_", str(x3 * 100))

        questions_and_answers[round(expected_value, 2)] = question_3

        return questions_and_answers

    def calculate_land_value(self, x1, x2, x3, y1, y2, base_land_value=400000, oil_price_per_barrel=90):
        """
        Calculate the expected value of the land based on the probabilities and oil quantities.

        :param x1: Probability of y1 barrels of oil
        :param x2: Probability of y2 barrels of oil
        :param x3: Probability of no oil
        :param y1: Number of barrels in outcome x1
        :param y2: Number of barrels in outcome x2
        :param base_land_value: Base value of the land without oil
        :param oil_price_per_barrel: Price of oil per barrel
        :return: Expected value of the land
        """
        # Calculate the value in each scenario
        value_with_y1 = base_land_value + (y1 * oil_price_per_barrel)
        value_with_y2 = base_land_value + (y2 * oil_price_per_barrel)
        value_with_no_oil = base_land_value

        # Calculate expected value
        expected_value = (x1 * value_with_y1) + (x2 * value_with_y2) + (x3 * value_with_no_oil)

        return expected_value

    def ev_hedge(self, x1, strike_price, y1, price_after_increase, price_after_decrease, y3, price_rebound, cost_of_option):
        """Calculate the expected value of the hedging strategy with a put option."""
        # Convert percentages to probabilities
        p_increase = y1 / 100
        p_decrease = 1 - p_increase
        p_rebound = y3 / 100

        # Prices and cost
        price_initial = x1

        # Value calculations
        # If stock price increases
        if price_after_increase > strike_price:
            value_increase = price_after_increase - cost_of_option
        else:
            value_increase = strike_price - price_after_increase - cost_of_option

        # If stock price decreases and rebounds
        if price_rebound > strike_price:
            value_rebound = price_rebound - cost_of_option
        else:
            value_rebound = strike_price - price_rebound - cost_of_option

        # If stock price decreases but does not rebound
        if price_after_decrease > strike_price:
            value_no_rebound = price_after_decrease - cost_of_option
        else:
            value_no_rebound = strike_price - price_after_decrease - cost_of_option

        # Expected value calculation
        ev = (p_increase * value_increase +
              p_decrease * (p_rebound * value_rebound + (1 - p_rebound) * value_no_rebound))

        return ev


    def ev_colored_balls(self, x1, x2, x3, y1):
        """Calculate the expected value of the colored balls game."""
        total_balls = x1 + x2 + x3
        p_correct = max(x1, x2, x3) / total_balls
        return p_correct * y1

    def prob_red_black_order(self, x2, x3):
        """Calculate the probability that the black balls are not next to each other."""
        total_permutations = math.factorial(x2 + x3) / (math.factorial(x2) * math.factorial(x3))
        # Calculate the number of arrangements where black balls are together
        if x3 > 1:
            black_together = (math.factorial(x2 + 1) / math.factorial(x2)) * math.comb(x3, 2)
        else:
            black_together = 0
        prob_not_together = (total_permutations - black_together) / total_permutations
        return prob_not_together

    def generate_valid_sequences(self, x2):
        """Generate a valid sequence with at least one tails."""
        while True:
            sequence = ''.join(random.choice(['H', 'T']) for _ in range(x2))
            if 'T' in sequence:
                return sequence

    def ev_unfair_coin(self, p_heads, num_flips, euro_for_num_heads, euro_for_seq, s1, s2):
        p_heads /= 100
        p_tails = 1 - p_heads
        p_exact_heads = (p_heads ** num_flips)
        def sequence_probability(seq):
            p_seq = 1
            for flip in seq:
                if flip == 'H':
                    p_seq *= p_heads
                elif flip == 'T':
                    p_seq *= p_tails
            return p_seq
        p_seq1 = sequence_probability(s1)
        p_seq2 = sequence_probability(s2)
        prob_exact_heads = p_exact_heads * euro_for_num_heads
        prob_seq1 = p_seq1 * euro_for_seq
        prob_seq2 = p_seq2 * euro_for_seq
        ev_game = prob_exact_heads + prob_seq1 + prob_seq2

        return ev_game




    def generate_ev_questions(self):
        questions_and_answers = {}

        # Template 1: Expected Value with Colored Balls
        x1 = random.randint(1, 4)  # Number of blue balls
        x2 = random.randint(1, 4)  # Number of red balls
        x3 = random.randint(1, 4)  # Number of green balls
        y1 = random.randint(1, 10)  # Dollar amount won for guessing correctly
        ev_colored_balls = self.ev_colored_balls(x1, x2, x3, y1)
        question_1 = self.templates["Expected_Value"]["template_1"].replace("_x1_", str(x1)).replace("_x2_",
                                                                                                     str(x2)).replace(
            "_x3_", str(x3)).replace("_y1_", str(y1))
        questions_and_answers[round(ev_colored_balls, 2)] = question_1

        # Template 2: Probability with Red and Black Balls
        x2 = random.randint(2, 5)  # Number of red balls
        x3 = random.randint(2, 4)  # Number of black balls
        x4 = x2 + x3  # Total number of balls
        prob_not_together = round(self.prob_red_black_order(x2, x3), 2)
        question_2 = self.templates["Expected_Value"]["template_2"].replace("_x1_", str(x4)).replace("_x2_",
                                                                                                     str(x2)).replace(
            "_x3_", str(x3)).replace("_x4_", str(x4))
        questions_and_answers[round(prob_not_together, 4)] = question_2

        # Template 3: Expected Value with Unfair Coin
        x1 = random.randint(55, 70)  # Probability of heads (in %)
        x2 = random.randint(3, 4)  # Number of flips
        y1 = random.randint(5, 20)  # Euro amount won for exact heads
        y2 = random.randint(2, 10)  # Euro amount won for specific sequences
        s1 = self.generate_valid_sequences(x2)  # Generate a valid sequence
        s2 = self.generate_valid_sequences(x2)  # Generate another valid sequence
        ev_unfair_coin = self.ev_unfair_coin(x1, x2, y1, y2, s1, s2)
        question_3 = self.templates["Expected_Value"]["template_3"].replace("_x1_", str(x1)).replace("_x2_",
                                                                                                     str(x2)).replace(
            "_y1_", str(y1)).replace("_y2_", str(y2)).replace("_s1_", s1).replace("_s2_", s2)
        questions_and_answers[round(ev_unfair_coin, 2)] = question_3

        return questions_and_answers


