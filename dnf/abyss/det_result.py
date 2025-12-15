# -*- coding:utf-8 -*-

__author__ = "723323692"
__version__ = '1.0'


class DetResult:
    def __init__(self):
        self.monster_xywh_list = []
        self.elite_monster_xywh_list = []
        self.boss_xywh_list = []
        self.loot_xywh_list = []
        self.gold_xywh_list = []
        self.door_xywh_list = []
        self.door_boss_xywh_list = []

        # self.hero_conf = -1
        self.hero_xywh = None

        self.card_num = 0
        self.continue_exist = False
        self.shop_exist = False
        self.menu_exist = False
        self.shop_mystery_exist = False
        self.sss_exist = False
        self.forward_exists = False
        self.ball_xywh_list = []
        self.hole_xywh_list = []

    # 定义 __str__ 方法，方便打印对象信息
    def __str__(self):
        return (f"DetResult(\n"
                f"  monster_xywh_list={self.monster_xywh_list},\n"
                f"  elite_monster_xywh_list={self.elite_monster_xywh_list},\n"
                f"  boss_xywh_list={self.boss_xywh_list},\n"
                f"  loot_xywh_list={self.loot_xywh_list},\n"
                f"  gold_xywh_list={self.gold_xywh_list},\n"
                f"  door_xywh_list={self.door_xywh_list},\n"
                f"  door_boss_xywh_list={self.door_boss_xywh_list},\n"
                # f"  hero_conf={self.hero_conf},\n"
                f"  hero_xywh={self.hero_xywh},\n"
                f"  card_num={self.card_num},\n"
                f"  continue_exist={self.continue_exist},\n"
                f"  shop_exist={self.shop_exist}, \n"
                f"  shop_mystery_exist={self.shop_mystery_exist}, \n"
                f"  menu_exist={self.menu_exist}, \n"
                f"  sss_exist={self.sss_exist}\n"
                f")")