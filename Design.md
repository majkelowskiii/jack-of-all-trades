## Design

**"Jack of All Trades"** is an app that helps the user train GTO (Game Theory Optimal) strategies for popular card games.

The adding of new game should be seamless and easily integrable.

For strat the app will consist of **Module 1 - No Limit Texas Hold'em Poker** and **Module 2 - Blackjack**.

Both games are played with the **deck** of cards consisting of 52 cards - 13 figures of 4 colors.
Blackjack can be played with multiple decks, called **shoe**.

### Module 1 - No Limit Texas Hold'em Poker

Important note from Deck perspective - in Texas Hold'em the **player's hole cards** can be reffered as **suited** or **off-suited** - meaning they are either the same (heart+heart) or different (heart+spade) suit.

Texas Hold'em Poker is played at the **Table** consisting of up to 9 or 10 players (9-handed, etc.).
It can be played with lower number of players, but require at least 2 players (Heads-up / Two-handed play).
Depending of the numbers of players there are various position at the table:
- There always must be Big Blind (BB), Small Blind (SB) and Dealer (also reffered as Button - BTN)
- In Heads-up one player is Big Blind and the other player is Small Blind and Dealer at once.
- The other position are, going counter clock-wise from Big Blind in the order:
- Big Blind (BB)
- Small Blind (SB)
- Button (Dealer) (BTN)
- Cut-off (CO)
- Hijack (HJ)
- Lojack (LJ)
- Middle Position (MP)
- Under The Gun + 2 (UTG+2)
- Under The Gun + 1 (UTG+1)
- Under The Gun (UTG)
In 8-handed play there is no UTG+1 and UTG+2.
In 6-handed play there is no UTG+1, UTG+2, MP and Lojack, however for the simplicity and the range-wise it is acceptable to say that Lojack is first to act (we can label it UTG).

The play:
Players has **chips**. When your **chip counts** drops to zero you are eliminated. No Limit says that there is no maximum bet - in some versions of poker there is maximum threshold. There are some rounds of betting, but MVP declares only Pre-flop game - meaning before the **community cards** are dealt. However, the game is played in a way that there are **3 streets** of community cards - flop (3 cards), turn (1 card) and river (1 card). 
The players can call or bet (raise) before the flop, in between of the streets and after river. The goal is to make the strongest hand out of any combination of 7 cards (2 of each players' cards - **hole cards** and 5 community cards). The ranking of hands can be found here: https://en.wikipedia.org/wiki/List_of_poker_hands . 

Player can win the pot by either showing the best hand **at showdown** (once the betting after river finished) or by making other players fold.

Players bet their chips to the **pot**.

The play before the flop is as follows:
Players in the positions of BB and SB **posts** the blinds. Small blind is usually 1/2 of the Big Blind, however there are some structures that says otherwise. 

There is also an ante - in online games usually posted by each player (1/8th or (1/<number_of_players>) * Big Blind), in live games they are posted usually by player on Big Blind - which is called **Big Blind Ante**. 

Blind structure is not the topic of this MVP, however in tournament play they raise, and this is called levels (levels are usually 15+ min long) and in cash games are fixed. Stack size is also commonly reffered in Multiples of Big Blind (eg. for the Level with 1000/500 (1000) [Big Blind pays 1000, Small Blind pays 500, Ante is 1000], when Player one has 15000 in stack, his stack size can also be reffered as 15BB). Stack size in big blinds are important to range evaluations.

The blinds and ante exists so the player has incentive to play the pots - they are considered **dead money** and improve pot-odds (part of strategy) that is also not the scope of this MVP. #TODO add pot-odds calculator

The game is played with single deck of cards. Each player is dealt 2 cards starting from Small Blind and dealt clock-wise.

After all players recieved they **hand** (their **hole cards**) - the phase **pre-flop** starts.

Starting from player directly on left from Big Blind, the betting starts - the player can has a **decision** - either call, bet (or re-raise) or fold.
- Should he bet:
- when he is the first player to bet (no-one bet before him) - the minimum bet is 2 times Big Blind, and it is considered **Raise-First-In (RFI)** [which is important for ranges],
- when other player raised before him, it will be considered 3-bet, 4-bet, and so on depending on how many players bet before (RFI in this logic is "2 bet", but that is not the phrase commonly used), and minimal bet is "last bet + (last bet - previous bet)" (for 3-bet pots the BB is considered previous bet).
- Should he fold - he will no longer take place in that **hand** (round of play) and next player has the same set of options.
- Should he call, it will be called a limp, if there were no bets before and the next player has the same set of options, or he can call a bet and that eventually might close the action.
If you have made a bet, which was re-raised (eg. 3-betted) you will have another turn of betting. Should all players call, Big Blind will also have a decision to made.
Once all the players "agreed" on the stake to play the pot - no re-raised and call. The flop is dealt - and the MVP stops here.

Some examples of hands will be provided later.

From the **ranges** perspective - the players has a set of hands they should play from each position. Basic strategy does not cover limping, so calling without previous raiser.
The ranges are constructed in a way that are shown in here: https://www.splitsuit.com/poker-ranges-reading - eg. KQo, AKs, 77 - meaning King-Queen Off-suit, Ace-King Suited, pair of Sevens. The Tens are reffered to as T rather than 10, to make this type of notation more one-char friendly (so KTs rather than K10s), although it is also fine to use the second one, though.