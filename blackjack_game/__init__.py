from typing import Dict, List, Tuple
import random
from mcdreforged.api.all import *

# 牌组定义
CARDS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
CARD_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11  # A默认为11，特殊处理
}

class PlayerHand:
    """玩家的一手牌"""
    __slots__ = ('cards', 'bet', 'stand', 'busted', 'doubled', 'surrendered', 'is_split')
    
    def __init__(self, cards: List[str], bet: float = 1.0, is_split: bool = False):
        self.cards = cards  # 牌列表
        self.bet = bet  # 下注倍数
        self.stand = False  # 是否停牌
        self.busted = False  # 是否爆牌
        self.doubled = False  # 是否双倍下注
        self.surrendered = False  # 是否投降
        self.is_split = is_split  # 是否来自分牌
    
    def add_card(self, card: str):
        """添加一张牌"""
        self.cards.append(card)
        self.check_bust()
    
    def check_bust(self):
        """检查是否爆牌"""
        _, busted = self.calculate_value()
        self.busted = busted
    
    def calculate_value(self) -> Tuple[int, bool]:
        """计算牌面点数和是否爆牌"""
        total = 0
        ace_count = 0
        
        # 计算基础点数
        for card in self.cards:
            if card == 'A':
                ace_count += 1
                total += 11
            else:
                total += CARD_VALUES[card]
        
        # 处理A的情况
        while total > 21 and ace_count > 0:
            total -= 10
            ace_count -= 1
        
        return total, total > 21
    
    def is_blackjack(self) -> bool:
        """检查是否是21点（Blackjack）- 必须由两张牌组成且不是分牌后"""
        if len(self.cards) != 2 or self.is_split:
            return False
        value, busted = self.calculate_value()
        return value == 21 and not busted
    
    def is_five_dragons(self) -> bool:
        """检查是否是五小龙（五张牌未爆）"""
        return len(self.cards) >= 5 and not self.busted
    
    def __str__(self) -> str:
        return ' '.join(self.cards)

class PlayerGame:
    """玩家游戏状态"""
    __slots__ = ('player', 'hands', 'dealer_hand', 'current_hand_index', 'score', 'in_game')
    
    def __init__(self, player: str):
        self.player = player  # 玩家名称
        self.hands: List[PlayerHand] = []  # 玩家多手牌
        self.dealer_hand: List[str] = []  # 庄家手牌
        self.current_hand_index = 0  # 当前操作的手牌索引
        self.score = 0.0  # 玩家当前分数
        self.in_game = False  # 是否在游戏中
    
    def start_new_round(self):
        """开始新一局游戏"""
        self.hands = [PlayerHand([])]
        self.dealer_hand = []
        self.current_hand_index = 0
        
        # 发牌：玩家2张，庄家2张（1张暗牌）
        for _ in range(2):
            self.hands[0].add_card(self.draw_card())
            self.dealer_hand.append(self.draw_card())
        
        self.in_game = True
    
    def draw_card(self) -> str:
        """随机抽取一张牌"""
        return random.choice(CARDS)
    
    def get_current_hand(self) -> PlayerHand:
        """获取当前操作的手牌"""
        return self.hands[self.current_hand_index]
    
    def next_hand(self) -> bool:
        """切换到下一手牌，返回是否还有手牌需要操作"""
        self.current_hand_index += 1
        return self.current_hand_index < len(self.hands)
    
    def hit(self):
        """玩家要牌"""
        hand = self.get_current_hand()
        if not hand.stand and not hand.busted and not hand.surrendered:
            hand.add_card(self.draw_card())
            
            # 五张牌未爆牌自动停牌（五小龙）
            if len(hand.cards) >= 5 and not hand.busted:
                hand.stand = True
    
    def stand(self):
        """玩家停牌"""
        hand = self.get_current_hand()
        if not hand.busted and not hand.surrendered:
            hand.stand = True
    
    def double_down(self) -> bool:
        """双倍下注，返回是否成功"""
        hand = self.get_current_hand()
        if len(hand.cards) == 2 and not hand.stand and not hand.busted and not hand.surrendered:
            hand.bet *= 2
            hand.doubled = True
            hand.add_card(self.draw_card())
            hand.stand = True
            return True
        return False
    
    def split(self) -> bool:
        """分牌，返回是否成功"""
        hand = self.get_current_hand()
        # 检查是否可以分牌：两张相同点数的牌，且手牌数量少于4（最多分4次）
        if (len(hand.cards) == 2 and 
            CARD_VALUES[hand.cards[0]] == CARD_VALUES[hand.cards[1]] and 
            len(self.hands) < 4):  # 最多4次分牌（5手牌）
            
            # 创建新手牌（标记为分牌）
            new_hand1 = PlayerHand([hand.cards[0]], hand.bet, is_split=True)
            new_hand2 = PlayerHand([hand.cards[1]], hand.bet, is_split=True)
            
            # 添加新牌
            new_hand1.add_card(self.draw_card())
            new_hand2.add_card(self.draw_card())
            
            # 替换当前手牌
            self.hands[self.current_hand_index] = new_hand1
            self.hands.append(new_hand2)
            return True
        return False
    
    def surrender(self) -> bool:
        """投降，返回是否成功"""
        hand = self.get_current_hand()
        if len(hand.cards) == 2 and not hand.stand and not hand.busted:
            hand.surrendered = True
            hand.stand = True
            return True
        return False
    
    def dealer_play(self):
        """庄家行动"""
        # 庄家规则：大于等于17点停牌，否则要牌
        while True:
            total, busted = self.calculate_dealer_value()
            if busted or total >= 17:
                break
            self.dealer_hand.append(self.draw_card())
    
    def calculate_dealer_value(self) -> Tuple[int, bool]:
        """计算庄家点数和是否爆牌"""
        total = 0
        ace_count = 0
        
        for card in self.dealer_hand:
            if card == 'A':
                ace_count += 1
                total += 11
            else:
                total += CARD_VALUES[card]
        
        while total > 21 and ace_count > 0:
            total -= 10
            ace_count -= 1
        
        return total, total > 21
    
    def settle_round(self):
        """结算当前游戏"""
        dealer_value, dealer_busted = self.calculate_dealer_value()
        round_score = 0
        
        # 结算每手牌
        for hand in self.hands:
            if hand.surrendered:
                round_score -= hand.bet * 0.5  # 投降损失一半下注
                continue
            
            if hand.busted:
                round_score -= hand.bet  # 爆牌损失全部下注
                continue
            
            hand_value, _ = hand.calculate_value()
            
            # 五小龙规则（五张牌未爆）且不是Blackjack
            if hand.is_five_dragons() and not hand.is_blackjack():
                round_score += hand.bet
                continue
            
            # Blackjack规则（只能由两张牌组成）
            if hand.is_blackjack():
                round_score += hand.bet * 1.5
                continue
            
            # 庄家爆牌，玩家获胜
            if dealer_busted:
                round_score += hand.bet
                continue
            
            # 普通比较
            if hand_value > dealer_value:
                round_score += hand.bet
            elif hand_value < dealer_value:
                round_score -= hand.bet
            # 平局不加分也不扣分
        
        # 更新玩家总分数
        self.score += round_score
        self.in_game = False
        return round_score

class BlackjackGame:
    """21点游戏管理器"""
    def __init__(self, server: PluginServerInterface):
        self.server = server
        self.player_games: Dict[str, PlayerGame] = {}
        self.help_msg = '''
§6===== 21点小游戏 =====
§e!!21 help§f - 显示帮助信息
§e!!21 start§f - 开始新游戏
§e!!21 stop§f - 结束游戏
§e!!21 h§f - 要牌
§e!!21 s§f - 停牌
§e!!21 d§f - 双倍下注
§e!!21 p§f - 分牌
§e!!21 sur§f - 投降

§6===== 游戏规则 =====
1. 目标: 点数接近21点但不超
2. A可计为1点或11点
3. 庄家规则: 点数≥17停牌
4. Blackjack: 仅初始两张牌组成21点(1.5倍)
5. 双倍下注: 奖励翻倍
6. 分牌: 相同点数可拆分(最多分4次)
7. 五小龙: 5张牌未爆直接获胜
8. 投降输一半
§6==================
'''.strip()

    def get_player_game(self, player: str) -> PlayerGame:
        """获取玩家游戏状态，不存在则创建"""
        if player not in self.player_games:
            self.player_games[player] = PlayerGame(player)
        return self.player_games[player]
    
    def start_game(self, player: str):
        """开始游戏"""
        game = self.get_player_game(player)
        if game.in_game:
            self.server.tell(player, "§c你已经在游戏中! 使用 !!21 stop 结束游戏")
            return
        
        game.start_new_round()
        self.display_game_state(player)
    
    def stop_game(self, player: str):
        """结束游戏"""
        if player in self.player_games:
            del self.player_games[player]
            self.server.tell(player, "§a游戏结束！")
        else:
            self.server.tell(player, "§a你当前没有进行中的游戏")
    
    def display_game_state(self, player: str):
        """显示当前游戏状态"""
        game = self.get_player_game(player)
        
        # 显示庄家手牌
        dealer_display = f"{game.dealer_hand[0]} ?" if len(game.dealer_hand) > 1 else ' '.join(game.dealer_hand)
        
        # 显示玩家所有手牌
        hands_display = []
        for i, hand in enumerate(game.hands):
            status = ""
            if hand.surrendered:
                status = "§8(投降)"
            elif hand.busted:
                status = "§c(爆牌)"
            elif hand.stand:
                status = "§a(停牌)"
            
            hand_prefix = f"手牌{i+1}:" if len(game.hands) > 1 else "你的牌:"
            if i == game.current_hand_index:
                hand_prefix = f"§e{hand_prefix}§f"
            
            hands_display.append(f"{hand_prefix} {hand} {status}")
        
        # 显示分数
        score_display = f"§6得分: §e{game.score:.1f}§f" if game.score % 1 > 0 else f"§6得分: §e{int(game.score)}§f"
        
        # 组合消息
        message = f"{score_display}\n{' '.join(hands_display)}\n§6庄家: {dealer_display}"
        self.server.tell(player, message)
    
    def process_command(self, player: str, command: str):
        """处理玩家命令"""
        game = self.get_player_game(player)
        
        if not game.in_game:
            self.server.tell(player, "§a你当前没有进行中的游戏, 使用§e!!21 start§a开始游戏")
            return
        
        command = command.lower()
        
        try:
            if command == 'h':  # 要牌
                game.hit()
                hand = game.get_current_hand()
                if hand.busted or hand.stand:
                    self.next_action(player)
                else:
                    self.display_game_state(player)
            
            elif command == 's':  # 停牌
                game.stand()
                self.next_action(player)
            
            elif command == 'd':  # 双倍下注
                if game.double_down():
                    self.next_action(player)
                else:
                    self.server.tell(player, "§c无法双倍下注, 只能在第一轮使用")
            
            elif command == 'p':  # 分牌
                if game.split():
                    self.display_game_state(player)
                else:
                    self.server.tell(player, "§c无法分牌, 只能分相同点数的牌")
            
            elif command == 'sur':  # 投降
                if game.surrender():
                    self.next_action(player)
                else:
                    self.server.tell(player, "§c无法投降, 只能在第一轮使用")
            
            else:
                self.server.tell(player, f"§c未知命令: {command}, 使用§e!!21 help§c查看帮助")
        
        except Exception as e:
            self.server.logger.error(f"处理21点命令时出错: {e}")
            self.server.tell(player, "§c命令执行出错, 请重试")
    
    def next_action(self, player: str):
        """处理下一步动作"""
        game = self.get_player_game(player)
        
        # 检查是否还有未操作的手牌
        if game.next_hand():
            self.display_game_state(player)
            return
        
        # 所有手牌操作完成，庄家行动
        game.dealer_play()
        
        # 结算游戏
        round_score = game.settle_round()
        score_sign = '+' if round_score >= 0 else ''
        round_score_display = f"{score_sign}{round_score:.1f}" if round_score % 1 > 0 else f"{score_sign}{int(round_score)}"
        
        # 显示最终结果
        dealer_cards = ' '.join(game.dealer_hand)
        dealer_value, _ = game.calculate_dealer_value()
        
        message = [
            f"§6===== 本局结束 =====",
            f"§a你的牌:"
        ]
        
        for i, hand in enumerate(game.hands):
            hand_value, _ = hand.calculate_value()
            if hand.surrendered:
                status = "§8(投降)"
            elif hand.busted:
                status = "§c(爆牌)"
            else:
                status = f"§a({hand_value}点)"
                
            hand_prefix = f"手牌{i+1}:" if len(game.hands) > 1 else ""
            message.append(f"§f{hand_prefix}{hand} {status}")
        
        message.extend([
            f"§6庄家: {dealer_cards} ({dealer_value}点)",
            f"§6本局得分: §e{round_score_display}",
            f"§6总得分: §e{game.score:.1f}" if game.score % 1 > 0 else f"§6总得分: §e{int(game.score)}",
            f"§6=================="
        ])
        
        self.server.tell(player, "\n".join(message))
        
        # 自动开始下一局
        self.server.tell(player, "§a自动开始下一局...")
        self.start_game(player)

def on_load(server: PluginServerInterface, old):
    """插件加载时执行"""
    game = BlackjackGame(server)
    
    # 注册命令
    server.register_command(
        Literal("!!21")
        .then(Literal("help").runs(lambda src: src.reply(game.help_msg)))
        .then(Literal("start").runs(lambda src: game.start_game(src.player)))
        .then(Literal("stop").runs(lambda src: game.stop_game(src.player)))
        .then(Literal("h").runs(lambda src: game.process_command(src.player, 'h')))
        .then(Literal("s").runs(lambda src: game.process_command(src.player, 's')))
        .then(Literal("d").runs(lambda src: game.process_command(src.player, 'd')))
        .then(Literal("p").runs(lambda src: game.process_command(src.player, 'p')))
        .then(Literal("sur").runs(lambda src: game.process_command(src.player, 'sur')))
    )
    # 保存实例
    server.register_help_message('!!21', '21点纸牌游戏')
    server.game = game
def on_unload(server: PluginServerInterface):
    """插件卸载时清理"""
    if hasattr(server, 'game'):
        del server.game
