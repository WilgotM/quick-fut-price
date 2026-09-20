"""Data models for FUTBIN SDK"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Platform(StrEnum):
    """游戏平台"""

    PS = "PS"
    PC = "PC"
    XBOX = "XB"  # Xbox 与 PS 共享市场


class CardVersion(StrEnum):
    """卡片版本"""

    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    RARE = "rare"
    NON_RARE = "non_rare"
    TOTW = "totw"
    TOTY = "toty"
    TOTS = "tots"
    ICON = "icon"
    HERO = "hero"


class PlayerPrice(BaseModel):
    """球员价格信息"""

    price: int = Field(default=0, description="当前价格")
    min_price: int = Field(default=0, description="最低价格")
    max_price: int = Field(default=0, description="最高价格")
    updated: str = Field(default="", description="更新时间")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PlayerPrice":
        """从 API 响应解析价格"""
        return cls(
            price=int(data.get("LCPrice", 0) or 0),
            min_price=int(data.get("MinPrice", 0) or 0),
            max_price=int(data.get("MaxPrice", 0) or 0),
            updated=str(data.get("updated", "")),
        )


class Player(BaseModel):
    """球员信息"""

    futbin_id: int = Field(description="FUTBIN ID")
    resource_id: int = Field(default=0, description="EA Resource ID")
    name: str = Field(default="", description="球员名称")
    rating: int = Field(default=0, description="评分")
    position: str = Field(default="", description="位置")
    club: str = Field(default="", description="俱乐部")
    league: str = Field(default="", description="联赛")
    nation: str = Field(default="", description="国籍")

    # 价格信息
    price_ps: PlayerPrice | None = Field(default=None, description="PS 平台价格")
    price_pc: PlayerPrice | None = Field(default=None, description="PC 平台价格")

    # 属性
    pace: int = Field(default=0, description="速度")
    shooting: int = Field(default=0, description="射门")
    passing: int = Field(default=0, description="传球")
    dribbling: int = Field(default=0, description="盘带")
    defending: int = Field(default=0, description="防守")
    physical: int = Field(default=0, description="身体")


class PopularPlayer(BaseModel):
    """热门球员"""

    futbin_id: int = Field(description="FUTBIN ID")
    resource_id: int = Field(default=0, description="EA Resource ID")
    name: str = Field(default="", description="球员名称")
    rating: int = Field(default=0, description="评分")
    price_ps: int = Field(default=0, description="PS 价格")
    price_pc: int = Field(default=0, description="PC 价格")


class FullPlayer(BaseModel):
    """完整球员信息（来自搜索/TOTW/最新球员 API）"""

    futbin_id: int = Field(description="FUTBIN ID")
    player_id: int = Field(default=0, description="球员 ID")
    resource_id: int = Field(default=0, description="EA Resource ID")
    name: str = Field(default="", description="球员名称")
    common_name: str = Field(default="", description="常用名")
    rating: int = Field(default=0, description="评分")
    position: str = Field(default="", description="主位置")
    positions: str = Field(default="", description="所有位置")
    rare_type: int = Field(default=0, description="稀有类型")

    # 俱乐部/国家/联赛
    club_id: int = Field(default=0, description="俱乐部 ID")
    club: str = Field(default="", description="俱乐部名称")
    nation_id: int = Field(default=0, description="国家 ID")
    nation: str = Field(default="", description="国家名称")
    league_id: int = Field(default=0, description="联赛 ID")
    league: str = Field(default="", description="联赛名称")

    # 六边形属性
    pace: int = Field(default=0, description="速度")
    shooting: int = Field(default=0, description="射门")
    passing: int = Field(default=0, description="传球")
    dribbling: int = Field(default=0, description="盘带")
    defending: int = Field(default=0, description="防守")
    physical: int = Field(default=0, description="身体")

    # 价格信息
    price_ps: int = Field(default=0, description="PS 价格")
    price_pc: int = Field(default=0, description="PC 价格")
    price_xbox: int = Field(default=0, description="Xbox 价格")
    min_price_ps: int = Field(default=0, description="PS 最低价")
    max_price_ps: int = Field(default=0, description="PS 最高价")
    min_price_pc: int = Field(default=0, description="PC 最低价")
    max_price_pc: int = Field(default=0, description="PC 最高价")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "FullPlayer":
        """从 API 响应解析球员"""
        return cls(
            futbin_id=int(data.get("ID", 0)),
            player_id=int(data.get("playerid", 0)),
            resource_id=int(data.get("resource_id", 0)),
            name=data.get("playername", "") or data.get("name", ""),
            common_name=data.get("common_name", ""),
            rating=int(data.get("rating", 0)),
            position=data.get("position", ""),
            positions=data.get("pos_all", ""),
            rare_type=int(data.get("raretype", 0)),
            club_id=int(data.get("club", 0)),
            club=data.get("club_name", ""),
            nation_id=int(data.get("nation", 0)),
            nation=data.get("nation_name", ""),
            league_id=int(data.get("league", 0)),
            league=data.get("league_name", ""),
            pace=int(data.get("pac", 0)),
            shooting=int(data.get("sho", 0)),
            passing=int(data.get("pas", 0)),
            dribbling=int(data.get("dri", 0)),
            defending=int(data.get("def", 0)),
            physical=int(data.get("phy", 0)),
            price_ps=int(data.get("ps_LCPrice", 0) or 0),
            price_pc=int(data.get("pc_LCPrice", 0) or 0),
            price_xbox=int(data.get("xbox_LCPrice", 0) or 0),
            min_price_ps=int(data.get("ps_MinPrice", 0) or 0),
            max_price_ps=int(data.get("ps_MaxPrice", 0) or 0),
            min_price_pc=int(data.get("pc_MinPrice", 0) or 0),
            max_price_pc=int(data.get("pc_MaxPrice", 0) or 0),
        )


class Foot(StrEnum):
    """惯用脚"""

    LEFT = "Left"
    RIGHT = "Right"


class PlayerSearchOptions(BaseModel):
    """球员搜索选项

    支持 40+ 详细属性筛选，与 matheusfm/futbin (Go) 完全对齐。
    """

    # 基础筛选
    platform: str = Field(default="PS", description="平台 (PS/PC)")
    page: int = Field(default=1, description="页码")
    sort: str | None = Field(default=None, description="排序字段")
    order: str | None = Field(default=None, description="排序方向 (asc/desc)")
    version: str | None = Field(default=None, description="卡片版本")

    # 球员属性
    position: list[str] | None = Field(default=None, description="位置列表")
    nation_id: int | None = Field(default=None, description="国家 ID")
    league_id: int | None = Field(default=None, description="联赛 ID")
    club_id: int | None = Field(default=None, description="俱乐部 ID")

    # 评分/价格范围
    min_rating: int | None = Field(default=None, description="最低评分")
    max_rating: int | None = Field(default=None, description="最高评分")
    min_price: int | None = Field(default=None, description="最低价格")
    max_price: int | None = Field(default=None, description="最高价格")

    # 技能/弱脚/惯用脚
    min_skills: int | None = Field(default=None, description="最低技能星级")
    max_skills: int | None = Field(default=None, description="最高技能星级")
    min_weak_foot: int | None = Field(default=None, description="最低弱脚星级")
    max_weak_foot: int | None = Field(default=None, description="最高弱脚星级")
    foot: Foot | None = Field(default=None, description="惯用脚")

    # 身体属性
    min_height: int | None = Field(default=None, description="最低身高 (cm)")
    max_height: int | None = Field(default=None, description="最高身高 (cm)")
    min_weight: int | None = Field(default=None, description="最低体重 (kg)")
    max_weight: int | None = Field(default=None, description="最高体重 (kg)")

    # 六边形属性范围
    min_pace: int | None = Field(default=None, description="最低速度")
    max_pace: int | None = Field(default=None, description="最高速度")
    min_shooting: int | None = Field(default=None, description="最低射门")
    max_shooting: int | None = Field(default=None, description="最高射门")
    min_passing: int | None = Field(default=None, description="最低传球")
    max_passing: int | None = Field(default=None, description="最高传球")
    min_dribbling: int | None = Field(default=None, description="最低盘带")
    max_dribbling: int | None = Field(default=None, description="最高盘带")
    min_defending: int | None = Field(default=None, description="最低防守")
    max_defending: int | None = Field(default=None, description="最高防守")
    min_physical: int | None = Field(default=None, description="最低身体")
    max_physical: int | None = Field(default=None, description="最高身体")

    # 详细速度属性
    min_acceleration: int | None = Field(default=None, description="最低加速")
    max_acceleration: int | None = Field(default=None, description="最高加速")
    min_sprint_speed: int | None = Field(default=None, description="最低冲刺速度")
    max_sprint_speed: int | None = Field(default=None, description="最高冲刺速度")

    # 详细射门属性
    min_positioning: int | None = Field(default=None, description="最低跑位")
    max_positioning: int | None = Field(default=None, description="最高跑位")
    min_finishing: int | None = Field(default=None, description="最低射术")
    max_finishing: int | None = Field(default=None, description="最高射术")
    min_shot_power: int | None = Field(default=None, description="最低射门力量")
    max_shot_power: int | None = Field(default=None, description="最高射门力量")
    min_long_shots: int | None = Field(default=None, description="最低远射")
    max_long_shots: int | None = Field(default=None, description="最高远射")
    min_volleys: int | None = Field(default=None, description="最低凌空")
    max_volleys: int | None = Field(default=None, description="最高凌空")
    min_penalties: int | None = Field(default=None, description="最低点球")
    max_penalties: int | None = Field(default=None, description="最高点球")

    # 详细传球属性
    min_vision: int | None = Field(default=None, description="最低视野")
    max_vision: int | None = Field(default=None, description="最高视野")
    min_crossing: int | None = Field(default=None, description="最低传中")
    max_crossing: int | None = Field(default=None, description="最高传中")
    min_free_kick: int | None = Field(default=None, description="最低任意球精度")
    max_free_kick: int | None = Field(default=None, description="最高任意球精度")
    min_short_passing: int | None = Field(default=None, description="最低短传")
    max_short_passing: int | None = Field(default=None, description="最高短传")
    min_long_passing: int | None = Field(default=None, description="最低长传")
    max_long_passing: int | None = Field(default=None, description="最高长传")
    min_curve: int | None = Field(default=None, description="最低弧线")
    max_curve: int | None = Field(default=None, description="最高弧线")

    # 详细盘带属性
    min_agility: int | None = Field(default=None, description="最低敏捷")
    max_agility: int | None = Field(default=None, description="最高敏捷")
    min_balance: int | None = Field(default=None, description="最低平衡")
    max_balance: int | None = Field(default=None, description="最高平衡")
    min_reactions: int | None = Field(default=None, description="最低反应")
    max_reactions: int | None = Field(default=None, description="最高反应")
    min_ball_control: int | None = Field(default=None, description="最低控球")
    max_ball_control: int | None = Field(default=None, description="最高控球")
    min_composure: int | None = Field(default=None, description="最低镇定")
    max_composure: int | None = Field(default=None, description="最高镇定")

    # 详细防守属性
    min_interceptions: int | None = Field(default=None, description="最低抢断")
    max_interceptions: int | None = Field(default=None, description="最高抢断")
    min_heading_accuracy: int | None = Field(default=None, description="最低头球精度")
    max_heading_accuracy: int | None = Field(default=None, description="最高头球精度")
    min_marking: int | None = Field(default=None, description="最低盯人")
    max_marking: int | None = Field(default=None, description="最高盯人")
    min_standing_tackle: int | None = Field(default=None, description="最低正面铲球")
    max_standing_tackle: int | None = Field(default=None, description="最高正面铲球")
    min_sliding_tackle: int | None = Field(default=None, description="最低滑铲")
    max_sliding_tackle: int | None = Field(default=None, description="最高滑铲")

    # 详细身体属性
    min_jumping: int | None = Field(default=None, description="最低弹跳")
    max_jumping: int | None = Field(default=None, description="最高弹跳")
    min_stamina: int | None = Field(default=None, description="最低耐力")
    max_stamina: int | None = Field(default=None, description="最高耐力")
    min_strength: int | None = Field(default=None, description="最低强壮")
    max_strength: int | None = Field(default=None, description="最高强壮")
    min_aggression: int | None = Field(default=None, description="最低侵略性")
    max_aggression: int | None = Field(default=None, description="最高侵略性")

    # 门将属性
    min_gk_diving: int | None = Field(default=None, description="最低门将扑救")
    max_gk_diving: int | None = Field(default=None, description="最高门将扑救")
    min_gk_handling: int | None = Field(default=None, description="最低门将手型")
    max_gk_handling: int | None = Field(default=None, description="最高门将手型")
    min_gk_kicking: int | None = Field(default=None, description="最低门将开球")
    max_gk_kicking: int | None = Field(default=None, description="最高门将开球")
    min_gk_positioning: int | None = Field(default=None, description="最低门将站位")
    max_gk_positioning: int | None = Field(default=None, description="最高门将站位")
    min_gk_reflexes: int | None = Field(default=None, description="最低门将反应")
    max_gk_reflexes: int | None = Field(default=None, description="最高门将反应")

    def _add_minmax_param(
        self,
        params: dict[str, str | int],
        key: str,
        min_val: int | None,
        max_val: int | None,
    ) -> None:
        """添加 min_*/max_* 格式的范围参数"""
        if min_val is not None:
            params[f"min_{key}"] = min_val
        if max_val is not None:
            params[f"max_{key}"] = max_val

    def to_params(self) -> dict[str, str | int]:
        """转换为 API 参数"""
        params: dict[str, str | int] = {
            "platform": self.platform,
            "page": self.page,
        }

        # 基础参数
        if self.sort:
            params["sort"] = self.sort
        if self.order:
            params["order"] = self.order
        if self.version:
            params["version"] = self.version
        if self.position:
            params["position"] = ",".join(self.position)
        if self.nation_id:
            params["nation"] = self.nation_id
        if self.league_id:
            params["league"] = self.league_id
        if self.club_id:
            params["club"] = self.club_id
        if self.foot:
            params["foot"] = self.foot.value

        # 所有范围参数使用 min_*/max_* 格式
        self._add_minmax_param(params, "rating", self.min_rating, self.max_rating)
        self._add_minmax_param(params, "price", self.min_price, self.max_price)
        self._add_minmax_param(params, "skills", self.min_skills, self.max_skills)
        self._add_minmax_param(params, "wf", self.min_weak_foot, self.max_weak_foot)
        self._add_minmax_param(params, "height", self.min_height, self.max_height)
        self._add_minmax_param(params, "weight", self.min_weight, self.max_weight)

        # 六边形属性
        self._add_minmax_param(params, "Pace", self.min_pace, self.max_pace)
        self._add_minmax_param(params, "Shooting", self.min_shooting, self.max_shooting)
        self._add_minmax_param(params, "Passing", self.min_passing, self.max_passing)
        self._add_minmax_param(params, "Dribbling", self.min_dribbling, self.max_dribbling)
        self._add_minmax_param(params, "Defending", self.min_defending, self.max_defending)
        self._add_minmax_param(params, "Physicality", self.min_physical, self.max_physical)

        # 详细速度
        self._add_minmax_param(params, "Acceleration", self.min_acceleration, self.max_acceleration)
        self._add_minmax_param(params, "Sprintspeed", self.min_sprint_speed, self.max_sprint_speed)

        # 详细射门
        self._add_minmax_param(params, "Positioning", self.min_positioning, self.max_positioning)
        self._add_minmax_param(params, "Finishing", self.min_finishing, self.max_finishing)
        self._add_minmax_param(params, "Shotpower", self.min_shot_power, self.max_shot_power)
        self._add_minmax_param(params, "Longshots", self.min_long_shots, self.max_long_shots)
        self._add_minmax_param(params, "Volleys", self.min_volleys, self.max_volleys)
        self._add_minmax_param(params, "Penalties", self.min_penalties, self.max_penalties)

        # 详细传球
        self._add_minmax_param(params, "Vision", self.min_vision, self.max_vision)
        self._add_minmax_param(params, "Crossing", self.min_crossing, self.max_crossing)
        self._add_minmax_param(params, "Freekickaccuracy", self.min_free_kick, self.max_free_kick)
        self._add_minmax_param(params, "Shortpassing", self.min_short_passing, self.max_short_passing)
        self._add_minmax_param(params, "Longpassing", self.min_long_passing, self.max_long_passing)
        self._add_minmax_param(params, "Curve", self.min_curve, self.max_curve)

        # 详细盘带
        self._add_minmax_param(params, "Agility", self.min_agility, self.max_agility)
        self._add_minmax_param(params, "Balance", self.min_balance, self.max_balance)
        self._add_minmax_param(params, "Reactions", self.min_reactions, self.max_reactions)
        self._add_minmax_param(params, "Ballcontrol", self.min_ball_control, self.max_ball_control)
        self._add_minmax_param(params, "Composure", self.min_composure, self.max_composure)

        # 详细防守
        self._add_minmax_param(params, "Interceptions", self.min_interceptions, self.max_interceptions)
        self._add_minmax_param(params, "Headingaccuracy", self.min_heading_accuracy, self.max_heading_accuracy)
        self._add_minmax_param(params, "Marking", self.min_marking, self.max_marking)
        self._add_minmax_param(params, "Standingtackle", self.min_standing_tackle, self.max_standing_tackle)
        self._add_minmax_param(params, "Slidingtackle", self.min_sliding_tackle, self.max_sliding_tackle)

        # 详细身体
        self._add_minmax_param(params, "Jumping", self.min_jumping, self.max_jumping)
        self._add_minmax_param(params, "Stamina", self.min_stamina, self.max_stamina)
        self._add_minmax_param(params, "Strength", self.min_strength, self.max_strength)
        self._add_minmax_param(params, "Aggression", self.min_aggression, self.max_aggression)

        # 门将
        self._add_minmax_param(params, "Gkdiving", self.min_gk_diving, self.max_gk_diving)
        self._add_minmax_param(params, "Gkhandling", self.min_gk_handling, self.max_gk_handling)
        self._add_minmax_param(params, "Gkkicking", self.min_gk_kicking, self.max_gk_kicking)
        self._add_minmax_param(params, "Gkpositioning", self.min_gk_positioning, self.max_gk_positioning)
        self._add_minmax_param(params, "Gkreflexes", self.min_gk_reflexes, self.max_gk_reflexes)

        return params


class ChemistryStyle(BaseModel):
    """化学卡"""

    name: str = Field(description="化学卡名称")
    ea_id: int = Field(default=0, description="EA ID (cardsubtypeid)")
    price_ps: int = Field(default=0, description="PS 平台价格")
    price_pc: int = Field(default=0, description="PC 平台价格")
    min_price_ps: int = Field(default=0, description="PS 最低价")
    max_price_ps: int = Field(default=0, description="PS 最高价")
    min_price_pc: int = Field(default=0, description="PC 最低价")
    max_price_pc: int = Field(default=0, description="PC 最高价")
    boost: str = Field(default="", description="加成属性")
    preferred_positions: list[str] = Field(default_factory=list, description="适用位置")


class ManagerCard(BaseModel):
    """教练员卡"""

    nation: str = Field(description="国籍")
    nation_id: int = Field(default=0, description="国籍 ID")
    bronze_price_ps: int = Field(default=0, description="铜卡 PS 价格")
    bronze_price_pc: int = Field(default=0, description="铜卡 PC 价格")
    silver_price_ps: int = Field(default=0, description="银卡 PS 价格")
    silver_price_pc: int = Field(default=0, description="银卡 PC 价格")
    gold_price_ps: int = Field(default=0, description="金卡 PS 价格")
    gold_price_pc: int = Field(default=0, description="金卡 PC 价格")


class LeagueCard(BaseModel):
    """联赛卡"""

    name: str = Field(description="联赛名称")
    league_id: int = Field(default=0, description="联赛 ID")
    price_ps: int = Field(default=0, description="PS 价格")
    price_pc: int = Field(default=0, description="PC 价格")


class League(BaseModel):
    """联赛信息"""

    league_id: int = Field(description="联赛 ID")
    name: str = Field(default="", description="联赛名称")
    clubs: list["Club"] = Field(default_factory=list, description="俱乐部列表")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "League":
        """从 API 响应解析联赛"""
        clubs = [Club.from_api_response(c) for c in data.get("clubs", [])]
        return cls(
            league_id=int(data.get("league_id", 0)),
            name=data.get("league_name", ""),
            clubs=clubs,
        )


class Club(BaseModel):
    """俱乐部信息"""

    club_id: int = Field(description="俱乐部 ID")
    name: str = Field(default="", description="俱乐部名称")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Club":
        """从 API 响应解析俱乐部"""
        return cls(
            club_id=int(data.get("club_id", 0)),
            name=data.get("club_name", ""),
        )


class CardVersionInfo(BaseModel):
    """卡片版本信息"""

    name: str = Field(default="", description="版本名称")
    key: str = Field(default="", description="版本键名")
    img: str = Field(default="", description="图片标识")

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "CardVersionInfo":
        """从 API 响应解析卡片版本"""
        return cls(
            name=data.get("version_name", ""),
            key=data.get("get", ""),
            img=data.get("img", ""),
        )


# 位置常量
class Position(StrEnum):
    """球员位置"""

    GK = "GK"
    RB = "RB"
    RWB = "RWB"
    LB = "LB"
    LWB = "LWB"
    CB = "CB"
    CDM = "CDM"
    CM = "CM"
    CAM = "CAM"
    RM = "RM"
    RW = "RW"
    RF = "RF"
    LM = "LM"
    LW = "LW"
    LF = "LF"
    CF = "CF"
    ST = "ST"
