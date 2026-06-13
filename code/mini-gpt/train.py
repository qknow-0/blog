#!/usr/bin/env python3
"""
微型 GPT 训练脚本 — 从零训一个能生成中文文本的模型。

默认用《三国演义》片段，也可以换成自己的 TXT 文件。

用法：
    cd code/mini-gpt
    uv run train.py              # 从头训练
    uv run train.py --gen        # 只生成（需要已训练好的模型）
    uv run train.py --file my.txt  # 用自己的文本训练

原理（五句话版）：
    1. 把文本按字切分成数字（每个汉字映射到一个编号）
    2. 随机截取一段数字，让模型猜每个位置的下一个字
    3. 猜错了就算损失（交叉熵），反向传播调参数
    4. 重复几千次，模型学会了「给定上文，下文应该是什么字」
    5. 生成时从起始字开始，一次预测一个字，加到上文里继续预测
"""

import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F

# ═══════════════════════════════════════════════════════════════
# 超参数 — 控制模型大小和训练行为的全局常量
# ═══════════════════════════════════════════════════════════════

# 上下文长度：模型一次能「看到」多少个字。
# 设为 128 意味着模型基于前面最多 128 个字来预测下一个字。
# 越大记越远，但计算量是平方增长（注意力矩阵是 BLOCK_SIZE × BLOCK_SIZE）。
BLOCK_SIZE = 128

# 每批样本数：每次训练步骤并行处理多少段文本。
# batch 越大训练越稳定，但越吃内存。32 适合 CPU 训练。
BATCH_SIZE = 32

# 嵌入维度：每个字被映射成多长的向量。
# 这个向量要装下字的语义信息。中文词表大（约 2000 字 vs 英文 65 字符），
# 所以用 192 而不是英文版常用的 128——给每个字更多「空间」来编码。
N_EMBD = 192

# 注意力头数：把嵌入向量拆成几份，每份独立做注意力计算。
# 类比：4 个人同时读同一段话，每人关注不同的东西——
# 一个关注主语，一个关注动词，一个关注标点，一个关注上下文关系。
N_HEAD = 4

# Transformer 层数：数据流过的注意力 + 前馈网络块的个数。
# 每加一层，模型能捕捉更远距离的依赖关系。
# 4 层对于小型语料够用了——太少欠拟合，太多过拟合且慢。
N_LAYER = 4

# 训练总步数：5000 步对于 6000 字的小语料足够了。
# 步骤太多会导致「过拟合」——模型把原文背下来了，生成时只会抄原文。
MAX_ITERS = 5000

# 每多少步打印一次 loss，用于观察训练是否正常。
EVAL_INTERVAL = 500

# 学习率：每一步参数更新的幅度。
# 太大：loss 震荡不收敛。太小：训不动。
# 3e-4 是 GPT 系列的经典经验值。
LEARNING_RATE = 3e-4

# 模型保存路径——训练完保存，生成时加载。
MODEL_PATH = "mini-gpt-cn.pt"


# ═══════════════════════════════════════════════════════════════
# 内置中文语料：《三国演义》前几回，约 6000 字。
#
# 为什么选《三国演义》：
#   - 风格统一（文言白话混合），模型容易学到连贯的叙事模式
#   - 人物多、对话多，模型能学到「某人曰：...」的对话格式
#   - 篇幅适中，6000 字刚好——太少学不到规律，太多训得慢
# ═══════════════════════════════════════════════════════════════
BUILTIN_TEXT = """
第一回 宴桃园豪杰三结义 斩黄巾英雄首立功

话说天下大势，分久必合，合久必分。周末七国分争，并入于秦。及秦灭之后，楚汉分争，又并入于汉。
汉朝自高祖斩白蛇而起义，一统天下，后来光武中兴，传至献帝，遂分为三国。推其致乱之由，殆始于桓灵二帝。
桓帝禁锢善类，崇信宦官。及桓帝崩，灵帝即位，大将军窦武、太傅陈蕃共相辅佐。时有宦官曹节等弄权，窦武陈蕃谋诛之，机事不密，反为所害，中涓自此愈横。

建宁二年四月望日，帝御温德殿。方升座，殿角狂风骤起。只见一条大青蛇，从梁上飞将下来，蟠于椅上。帝惊倒，左右急救入宫，百官俱奔避。
须臾，蛇不见了。忽然大雷大雨，加以冰雹，落到半夜方止，坏却房屋无数。建宁四年二月，洛阳地震；又海水泛溢，沿海居民，尽被大浪卷入海中。
光和元年，雌鸡化雄。六月朔，黑气十余丈，飞入温德殿中。秋七月，有虹现于玉堂；五原山岸，尽皆崩裂。种种不祥，非止一端。
帝下诏问群臣以灾异之由，议郎蔡邕上疏，以为蜺堕鸡化，乃妇寺干政之所致，言颇切直。帝览奏叹息，因起更衣。曹节在后窃视，悉宣告左右；遂以他事陷邕于罪，放归田里。
后张让、赵忠、封谞、段珪、曹节、侯览、蹇硕、程旷、夏恽、郭胜十人朋比为奸，号为十常侍。帝尊信张让，呼为阿父。朝政日非，以致天下人心思乱，盗贼蜂起。

时巨鹿郡有兄弟三人：一名张角，一名张宝，一名张梁。那张角本是个不第秀才，因入山采药，遇一老人，碧眼童颜，手执藜杖，唤角至一洞中，以天书三卷授之，曰：此名太平要术，汝得之，当代天宣化，普救世人；若萌异心，必获恶报。角拜问姓名。老人曰：吾乃南华老仙也。言讫，化阵清风而去。角得此书，晓夜攻习，能呼风唤雨，号为太平道人。

中平元年正月内，疫气流行，张角散施符水，为人治病，自称大贤良师。角有徒弟五百余人，云游四方，皆能书符念咒。次后徒众日多，角乃立三十六方，大方万余人，小方六七千，各立渠帅，称为将军；讹言：苍天已死，黄天当立；岁在甲子，天下大吉。令人各以白土书甲子二字于家中大门上。青幽徐冀荆扬兖豫八州之人，家家侍奉大贤良师张角名字。
角遣其党马元义，暗赍金帛，结交中涓封谞，以为内应。角与二弟商议曰：至难得者，民心也。今民心已顺，若不乘势取天下，诚为可惜。遂一面私造黄旗，约期举事。一面使弟子唐周，驰书报封谞。唐周乃径赴省中告变。帝召大将军何进调兵擒马元义，斩之；次收封谞等一干人下狱。张角闻知事露，星夜举兵，自称天公将军，张宝称地公将军，张梁称人公将军。
申言于众曰：今汉运将终，大圣人出。汝等皆宜顺天从正，以乐太平。四方百姓，裹黄巾从张角反者四五十万。贼势浩大，官军望风而靡。何进奏帝火速降诏，令各处备御，讨贼立功。一面遣中郎将卢植、皇甫嵩、朱隽，各引精兵，分三路讨之。

且说张角一军，前犯幽州界分。幽州太守刘焉，乃江夏竟陵人氏，汉鲁恭王之后也。当时闻得贼兵将至，召校尉邹靖计议。靖曰：贼兵众，我兵寡，明公宜作速招军应敌。刘焉然其说，随即出榜招募义兵。
榜文行到涿县，引出涿县中一个英雄。那人不甚好读书；性宽和，寡言语，喜怒不形于色；素有大志，专好结交天下豪杰；生得身长七尺五寸，两耳垂肩，双手过膝，目能自顾其耳，面如冠玉，唇若涂脂；中山靖王刘胜之后，汉景帝阁下玄孙，姓刘名备，字玄德。昔刘胜之子刘贞，汉武时封涿鹿亭侯，后坐酎金失侯，因此遗这一枝在涿县。
玄德祖刘雄，父刘弘。弘曾举孝廉，亦尝作吏，早丧。玄德幼孤，事母至孝；家贫，贩屦织席为业。家住本县楼桑村。其家之东南，有一大桑树，高五丈余，遥望之，童童如车盖。相者云：此家必出贵人。玄德幼时，与乡中小儿戏于树下，曰：我为天子，当乘此车盖。叔父刘元起奇其言，曰：此儿非常人也！因见玄德家贫，常资给之。

及刘焉发榜招军时，玄德年已二十八岁矣。当日见了榜文，慨然长叹。随后一人厉声言曰：大丈夫不与国家出力，何故长叹？玄德回视其人，身长八尺，豹头环眼，燕颔虎须，声若巨雷，势如奔马。玄德见他形貌异常，问其姓名。其人曰：某姓张名飞，字翼德。世居涿郡，颇有庄田，卖酒屠猪，专好结交天下豪杰。恰才见公看榜而叹，故此相问。
玄德曰：我本汉室宗亲，姓刘名备。今闻黄巾倡乱，有志欲破贼安民，恨力不能，故长叹耳。飞曰：吾颇有资财，当招募乡勇，与公同举大事，如何。玄德甚喜，遂与同入村店中饮酒。

正饮间，见一大汉，推着一辆车子，到店门首歇了，入店坐下，便唤酒保：快斟酒来吃，我待赶入城去投军。玄德看其人：身长九尺，髯长二尺；面如重枣，唇若涂脂；丹凤眼，卧蚕眉，相貌堂堂，威风凛凛。玄德就邀他同坐，叩其姓名。其人曰：吾姓关名羽，字云长，河东解良人也。因本处势豪倚势凌人，被吾杀了，逃难江湖，五六年矣。今闻此处招军破贼，特来应募。
玄德遂以己志告之，云长大喜。同到张飞庄上，共议大事。飞曰：吾庄后有一桃园，花开正盛；明日当于园中祭告天地，我三人结为兄弟，协力同心，然后可图大事。玄德、云长齐声应曰：如此甚好。

次日，于桃园中，备下乌牛白马祭礼等项，三人焚香再拜而说誓曰：念刘备、关羽、张飞，虽然异姓，既结为兄弟，则同心协力，救困扶危；上报国家，下安黎庶。不求同年同月同日生，只愿同年同月同日死。皇天后土，实鉴此心，背义忘恩，天人共戮！誓毕，拜玄德为兄，关羽次之，张飞为弟。祭罢天地，复宰牛设酒，聚乡中勇士，得三百余人，就桃园中痛饮一醉。
"""


# ═══════════════════════════════════════════════════════════════
# 第一步：加载数据
# ═══════════════════════════════════════════════════════════════

def load_data(file_path=None):
    """
    加载训练文本。默认用内置《三国演义》片段，
    也可以传 --file 参数指向自己的 TXT 文件。

    返回：原始文本字符串（越长效果越好，但 6000 字已经能出效果）
    """
    if file_path:
        print(f"📂 从文件加载: {file_path}")
        with open(file_path, encoding="utf-8") as f:
            text = f.read()
    else:
        print("📖 使用内置《三国演义》片段")
        text = BUILTIN_TEXT

    print(f"   总字符数: {len(text):,}")
    return text


# ═══════════════════════════════════════════════════════════════
# 第二步：分词器（Tokenizer）
#
# 把文本转成数字序列，这是模型唯一理解的输入格式。
# 这里用「字符级」分词——每个汉字就是一个独立 token。
#
# 为什么不 BPE/子词分词？
#   - 单个汉字本身就是有意义的单位，拆开反而丢失信息
#   - 实现极简——不需要训练分词器，不需要词表文件
#   - 词表大小可控——6000 字的小说只有约 1900 个不重复汉字
# ═══════════════════════════════════════════════════════════════

def build_tokenizer(text):
    """
    构建字符级分词器。
    返回三个值：
      encode: 字符串 → 整数列表
      decode: 整数列表 → 字符串
      vocab_size: 词表大小（模型输出层的维度）
    """
    # 去重排序——得到「这个文本里出现了哪些字」
    chars = sorted(list(set(text)))
    vocab_size = len(chars)

    # 双向映射表：字符 ↔ 序号
    # stoi: String TO Index。给一个字，返回它的编号。
    # itos: Index TO String。给一个编号，返回对应的字。
    stoi = {ch: i for i, ch in enumerate(chars)}
    itos = {i: ch for i, ch in enumerate(chars)}
    print(f"   词表大小: {vocab_size}（字符级）")

    def encode(s):
        """
        把字符串变成数字列表。
        如果遇到词表里没有的字（处理其他文本时可能出现），
        用 0 作为兜底——这是安全的，不会崩溃。
        """
        return [stoi.get(c, 0) for c in s]

    def decode(ids):
        """
        把数字列表变回字符串。
        如果遇到无效编号（不应该发生），用 □ 占位提示。
        """
        return "".join([itos.get(i, "□") for i in ids])

    return encode, decode, vocab_size


# ═══════════════════════════════════════════════════════════════
# 第三步：构建训练样本
#
# 训练任务：「给定上文，预测下一个字」。
# 所以每一对 (x, y) 是：
#   x = 「前 BLOCK_SIZE 个字」
#   y = 「这 BLOCK_SIZE 个字各自的下一个字」
#
# 比如 x = 「话说天下大」，y = 「说天下大势」（每个位置右移一位）
# ═══════════════════════════════════════════════════════════════

def prepare_data(encode, text):
    """
    把全文编码成 PyTorch 张量，然后按 9:1 切分训练集和验证集。
    验证集不参与训练——只用来检查过拟合（如果在训练集上 loss 很低
    但在验证集上 loss 开始上升，说明模型在「背课文」而不是在学规律）。

    返回：(train_data, val_data) 两个一维 LongTensor
    """
    data = torch.tensor(encode(text), dtype=torch.long)
    n = int(0.9 * len(data))       # 前 90% 训练
    return data[:n], data[n:]     # 后 10% 验证


def get_batch(split, train_data, val_data):
    """
    从训练集或验证集中随机取一批样本。
    每批 BATCH_SIZE 个样本，每个样本 BLOCK_SIZE 个字。

    x 和 y 的关系：
      x[i] = data[offset + i]                     # 第 i 个输入字
      y[i] = data[offset + i + 1]                 # 它的下一个字
    也就是说 y 是 x 向右平移一位得到的。
    模型的任务就是：给 x，预测 y。
    """
    data = train_data if split == "train" else val_data

    # 随机选 BATCH_SIZE 个起点（确保起点 + BLOCK_SIZE 不超过数据末尾）
    ix = torch.randint(len(data) - BLOCK_SIZE, (BATCH_SIZE,))

    # x: 从每个起点取 BLOCK_SIZE 个连续字
    x = torch.stack([data[i : i + BLOCK_SIZE] for i in ix])

    # y: 从每个起点+1 取 BLOCK_SIZE 个连续字（就是 x 的每一个位置的下一个字）
    y = torch.stack([data[i + 1 : i + BLOCK_SIZE + 1] for i in ix])

    return x, y


# ═══════════════════════════════════════════════════════════════
# 第四步：Transformer 模型
#
# 结构（自底向上）：
#   Head               — 单头自注意力：给定上文，算每个字应该「关注」哪些前文
#   MultiHeadAttention — 多头注意力：多个 Head 并行，各自关注不同维度
#   FeedForward        — 前馈网络：对每个位置的向量做非线性变换
#   Block              — Transformer 块 = 注意力 + 前馈 + 残差连接 + LayerNorm
#   MiniGPT            — 完整模型 = Embedding + N 个 Block + 输出投影
#
# 关键设计决策：
#   - 残差连接（x = x + f(x)）：让梯度能跳过层直接回传，防止深层网络训不动
#   - LayerNorm（层归一化）：把每层的输出拉到标准分布，让训练更稳定
#   - 因果注意力掩码（tril 矩阵）：确保第 i 个字只能看到第 0..i 个字，
#     不能偷看后面的字——否则就是「作弊」，训练和生成行为不一致
# ═══════════════════════════════════════════════════════════════

class Head(nn.Module):
    """
    单头自注意力——Transformer 的核心计算单元。

    做了什么（三步）：
      1. 每个字通过 Q(Query) 和 K(Key) 两套线性投影，算「我应该关注谁」
      2. 用下三角矩阵遮掉后面的字（因果掩码）→ softmax 得到关注权重
      3. 用权重对 V(Value) 做加权求和——「取我该关注的字的信息」

    输入形状：(B, T, C)  其中 B=batch, T=序列长度, C=嵌入维度
    输出形状：(B, T, head_size)
    """

    def __init__(self, head_size):
        super().__init__()
        # Q/K/V 三套投影——都是不带 bias 的线性层。
        # 不带 bias 是因为 LayerNorm 已经做了中心化，bias 多余。
        self.key = nn.Linear(N_EMBD, head_size, bias=False)    # 我「有什么」
        self.query = nn.Linear(N_EMBD, head_size, bias=False)  # 我「找什么」
        self.value = nn.Linear(N_EMBD, head_size, bias=False)  # 我「传什么」

        # 下三角矩阵：tril[i,j] = 1 当 j ≤ i，否则 0。
        # 这是 GPT 和 BERT 的关键区别——GPT 用因果掩码（只看前文），
        # BERT 不用（可以看双向）。
        # register_buffer 表示这不是参数，不参与梯度更新，但会跟着模型保存。
        self.register_buffer(
            "tril", torch.tril(torch.ones(BLOCK_SIZE, BLOCK_SIZE))
        )

    def forward(self, x):
        B, T, C = x.shape  # batch, 序列长度, 嵌入维度

        # Q @ K^T：算出每两个字之间的「相关性分数」矩阵 (T, T)
        # 除以 sqrt(C) 是 scale 操作——防止点积过大导致 softmax 梯度消失
        k = self.key(x)    # (B, T, head_size)
        q = self.query(x)  # (B, T, head_size)
        wei = q @ k.transpose(-2, -1) * C**-0.5  # (B, T, T)
        #                ^^^^^^^^^^ 转置最后两维做矩阵乘法

        # 因果掩码：把「未来」位置的分值设为 -inf。
        # softmax(-inf) = 0，所以模型无法「偷看」后面的字。
        wei = wei.masked_fill(self.tril[:T, :T] == 0, float("-inf"))

        # softmax 归一化：每行的权重加起来等于 1
        wei = F.softmax(wei, dim=-1)  # (B, T, T)——注意力权重矩阵

        # 用权重矩阵对 value 做加权求和
        v = self.value(x)  # (B, T, head_size)
        out = wei @ v       # (B, T, head_size)

        return out


class MultiHeadAttention(nn.Module):
    """
    多头注意力——同时跑多个 Head，每个关注不同方面。

    为什么需要多头？
      单头可能只关注「紧挨着的前一个字」，看不到更远或不同类型的关系。
      多头各自学不同的关注模式——一个头关注语法，一个头关注语义，
      一个头关注节奏——最后拼接起来形成更丰富的理解。
    """

    def __init__(self, num_heads, head_size):
        super().__init__()
        # 多个并行的 Head，每个输出 head_size 维向量
        self.heads = nn.ModuleList([Head(head_size) for _ in range(num_heads)])

        # 把拼接后的结果投影回原始嵌入维度——让信息在各个头之间融合
        self.proj = nn.Linear(N_EMBD, N_EMBD)

    def forward(self, x):
        # 每个 Head 独立计算 → 在最后一维拼接 → 投影
        # 拼接后维度 = num_heads * head_size = N_EMBD（因为 head_size = N_EMBD // N_HEAD）
        out = torch.cat([h(x) for h in self.heads], dim=-1)
        out = self.proj(out)
        return out


class FeedForward(nn.Module):
    """
    前馈网络——对每个位置独立做非线性变换。

    结构：Linear → ReLU → Linear
    第一层扩到 4 倍（让模型有更大的「思考空间」），
    第二层缩回来（保持维度一致，方便堆叠）。

    为什么需要它？
      注意力只做「信息聚合」（从不同位置收集信息）。
      前馈网络做「信息加工」（对聚合后的信息做理解和转换）。
      两者搭配才构成完整的「理解 + 推理」能力。
    """

    def __init__(self, n_embd):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd),  # 升维——给 ReLU 更大的空间
            nn.ReLU(),                        # 非线性——让模型不只是一个线性函数
            nn.Linear(4 * n_embd, n_embd),   # 降维——恢复原始大小
        )

    def forward(self, x):
        return self.net(x)


class Block(nn.Module):
    """
    一个 Transformer Block，GPT 的基本构建块。

    结构（按数据流顺序）：
      x → LayerNorm → 多头自注意力 → 残差(+) →
        → LayerNorm → 前馈网络    → 残差(+) → 输出

    两个关键设计：
      1. 残差连接（x = x + f(LayerNorm(x))）：
         跳过子层，让原始信息直接流到后面。没有它，深层网络的
         梯度会在反向传播中消失，根本训不动。
      2. Pre-LayerNorm（先归一化再进子层）：
         把输入拉到标准分布再计算——比 Post-LN 训练更稳定。
         GPT-2 开始就一直用 Pre-LN。
    """

    def __init__(self, n_embd, n_head):
        super().__init__()
        head_size = n_embd // n_head  # 每个 Head 的维度（N_EMBD / N_HEAD = 192/4 = 48）
        self.sa = MultiHeadAttention(n_head, head_size)   # 自注意力子层
        self.ffwd = FeedForward(n_embd)                    # 前馈子层
        self.ln1 = nn.LayerNorm(n_embd)  # 注意力前的归一化
        self.ln2 = nn.LayerNorm(n_embd)  # 前馈前的归一化

    def forward(self, x):
        # 1. 自注意力 + 残差：让每个字「和前面的字交流」
        x = x + self.sa(self.ln1(x))
        # 2. 前馈 + 残差：对交流结果做非线性加工
        x = x + self.ffwd(self.ln2(x))
        return x


class MiniGPT(nn.Module):
    """
    完整的 GPT 模型——和 GPT-2 架构一致，只是参数少了几个数量级。

    数据流：
      输入字序号 → Token Embedding → + Position Embedding →
      → N_LAYER 个 Transformer Block → LayerNorm → Linear → 输出概率

    输出是 vocab_size 维的向量，每个值代表对应字是「下一个字」的概率（logits）。
    """

    def __init__(self, vocab_size):
        super().__init__()

        # 词嵌入表：vocab_size 行 × N_EMBD 列。
        # 一行就是一个字的「向量表示」——语义相近的字在向量空间中靠得近。
        self.token_embedding_table = nn.Embedding(vocab_size, N_EMBD)

        # 位置嵌入表：BLOCK_SIZE 行 × N_EMBD 列。
        # 注意力机制本身不关心顺序（所有位置地位平等），
        # 所以需要把位置信息「注入」到每个字的向量里。
        # 第 0 行对应位置 0，第 1 行对应位置 1，以此类推。
        self.position_embedding_table = nn.Embedding(BLOCK_SIZE, N_EMBD)

        # N_LAYER 个 Transformer Block 顺序堆叠。
        # 每个 Block 处理上一层 Block 的输出，逐步加深理解。
        self.blocks = nn.Sequential(
            *[Block(N_EMBD, N_HEAD) for _ in range(N_LAYER)]
        )

        # 最后一层 LayerNorm——在输出前对特征做归一化
        self.ln_f = nn.LayerNorm(N_EMBD)

        # lm_head：把嵌入向量映射回词表空间。
        # 输入是 (B, T, N_EMBD)，输出是 (B, T, vocab_size)。
        # 每一行是这个位置对「词表中每个字是正确答案」的打分（logits）。
        self.lm_head = nn.Linear(N_EMBD, vocab_size)

        # 权重初始化——很重要，不好的初始化会导致训练不收敛
        self.apply(self._init_weights)

    def _init_weights(self, module):
        """
        GPT 标准的初始化策略：
          - 线性层：均值为 0、标准差为 0.02 的正态分布。
            为什么 0.02？——经验值，能让深层网络的激活值保持稳定。
          - Embedding：同上。
          - bias：初始化为 0。
        """
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx, targets=None):
        """
        前向传播——模型跑一次。

        参数：
          idx:     输入字序号    (B, T)
          targets: 正确答案序号  (B, T)，训练时传入，生成时不传

        返回：
          logits:  每个位置对每个字的打分  (B, T, vocab_size)
          loss:    交叉熵——预测和正确答案的差距（仅训练时返回）
        """
        B, T = idx.shape

        # 词嵌入：把字序号变成 N_EMBD 维向量
        tok_emb = self.token_embedding_table(idx)  # (B, T, N_EMBD)

        # 位置嵌入：告诉模型「这是第几个字」
        pos_emb = self.position_embedding_table(
            torch.arange(T, device=idx.device)
        )  # (T, N_EMBD)

        # 两者相加——每个字的向量 = 字义 + 位置
        x = tok_emb + pos_emb  # (B, T, N_EMBD)

        # 通过 N_LAYER 个 Transformer Block
        x = self.blocks(x)     # (B, T, N_EMBD)

        # 最后的归一化
        x = self.ln_f(x)       # (B, T, N_EMBD)

        # 投影到词表维度——每个位置对每个字打一个分
        logits = self.lm_head(x)  # (B, T, vocab_size)

        # 生成模式：只推理不训练，返回 logits 给 generate() 用
        if targets is None:
            return logits, None

        # 训练模式：算交叉熵损失
        # PyTorch 的 cross_entropy 要求输入是 (N, C) 和 (N,)
        # 所以把 (B, T, vocab_size) 展成 (B*T, vocab_size)
        #    把 (B, T) 展成 (B*T,)
        B, T, C = logits.shape
        logits = logits.view(B * T, C)
        targets = targets.view(B * T)
        loss = F.cross_entropy(logits, targets)
        #          ^^^^^^^^^^^^
        #          -log(正确字的概率) 的平均值。
        #          loss 越小表示模型预测越准。
        #          随机猜测时 loss ≈ ln(vocab_size) ≈ 7.5（~1900 个选项）。
        #          降到 1.5 以下时模型开始能输出连贯的文本。

        return logits, loss

    @torch.no_grad()  # 生成时关掉梯度计算——节省内存，加速推理
    def generate(self, idx, max_new_tokens, temperature=1.0):
        """
        自回归生成——一个字一个字地生成文本。

        参数：
          idx:              起始字序号    (1, T)
          max_new_tokens:   要生成多少个新字
          temperature:      温度。<1 保守（选高分字），>1 奔放（敢选低分字）

        过程：
          for _ in range(max_new_tokens):
              1. 用当前所有字作为输入，跑一次 forward
              2. 取最后一个位置的 logits（即模型对下一个字的预测）
              3. 除以 temperature 调整概率分布的「锋利度」
              4. softmax 转成概率
              5. 按概率随机采样一个字的序号（multinomial）
              6. 把这个字拼到末尾
              7. 重复
        """
        for _ in range(max_new_tokens):
            # 截断到 BLOCK_SIZE——如果序列超过了上下文窗口，只保留最后 BLOCK_SIZE 个字
            idx_cond = idx[:, -BLOCK_SIZE:]

            # 跑模型——拿到每个位置对每个字的打分
            logits, _ = self(idx_cond)   # (1, T, vocab_size)

            # 只取最后一个位置的预测——因为我们只需要「下一个字」
            logits = logits[:, -1, :]     # (1, vocab_size)

            # 温度缩放：temperature < 1 拉大分数差距，高分选项更占优势（保守）
            #          temperature > 1 缩小差距，低分选项也有机会（创造性强）
            logits = logits / temperature

            # softmax：把分数转成概率（所有字的概率加起来为 1）
            probs = F.softmax(logits, dim=-1)

            # multinomial：按概率随机采样一个字的序号。
            # 不是永远选最高分的字——加入随机性让每次生成结果不同。
            idx_next = torch.multinomial(probs, num_samples=1)  # (1, 1)

            # 把新字拼到末尾——下一次循环它会成为输入的一部分
            idx = torch.cat((idx, idx_next), dim=1)  # (1, T+1)

        return idx


# ═══════════════════════════════════════════════════════════════
# 第五步：训练循环
#
# 每一轮训练做的事：
#   1. 随机取一批训练数据（get_batch）
#   2. 前向传播——模型预测并算 loss（model(x, y)）
#   3. 反向传播——计算每个参数对 loss 的贡献（loss.backward()）
#   4. 更新参数——朝 loss 下降的方向微调（optimizer.step()）
#   5. 清空梯度——准备下一轮（optimizer.zero_grad()）
#
# 每 EVAL_INTERVAL 步在验证集上评估一次：
#   - 如果 train loss 在降但 val loss 开始升 → 过拟合，该停了
#   - 如果两个都在降 → 继续训
# ═══════════════════════════════════════════════════════════════

def train(model, train_data, val_data):
    """
    训练模型。

    AdamW 优化器说明：
      Adam = 自适应学习率 + 动量（积累梯度方向，加速收敛）
      AdamW = Adam + 权重衰减解耦（W 表示 decoupled Weight decay）
      权重衰减是一种正则化——每次更新时把参数往 0 方向拉一点，
      防止参数变得太大（过拟合的信号）。
    """
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    print(f"\n🔥 开始训练（{MAX_ITERS} 步）...\n")

    for step in range(MAX_ITERS):

        # --- 定期评估：检查过拟合 ---
        if step % EVAL_INTERVAL == 0:
            model.eval()  # 切到评估模式（关掉 dropout 等训练专用操作）
            with torch.no_grad():  # 关掉梯度计算（评估不需要，省内存）
                _, train_loss = model(*get_batch("train", train_data, val_data))
                _, val_loss = model(*get_batch("val", train_data, val_data))
            print(
                f"   step {step:5d} | "
                f"train loss {train_loss:.4f} | "
                f"val loss {val_loss:.4f}"
            )
            model.train()  # 切回训练模式

        # --- 训练一步 ---
        # 1. 取一批数据
        xb, yb = get_batch("train", train_data, val_data)

        # 2. 前向传播（算预测 + 算损失）
        _, loss = model(xb, yb)

        # 3. 清空上一轮的梯度——PyTorch 默认累加梯度，不手动清零会越积越多
        #    set_to_none=True 比 zero_() 稍快——直接释放内存而不是写零
        optimizer.zero_grad(set_to_none=True)

        # 4. 反向传播：计算 loss 对每个参数的梯度
        loss.backward()

        # 5. 更新参数：沿着梯度方向走一步（步长 = LEARNING_RATE）
        optimizer.step()

    print(f"\n✅ 训练完成！")
    return model


# ═══════════════════════════════════════════════════════════════
# 第六步：生成文本
# ═══════════════════════════════════════════════════════════════

def generate(model, encode, decode, temperature=0.8):
    """
    用训练好的模型生成文本。

    给几个不同的起始提示（prompt），对每个提示生成 80 个字。
    温度 0.8 是经验值——比默认 1.0 稍保守，减少乱码但保留多样性。
    """
    print(f"\n📝 生成（temperature={temperature}）...\n")

    # 用不同的起始短语——观察模型在不同上下文下的续写能力
    prompts = ["刘备", "关羽", "却说", "忽然"]

    for prompt in prompts:
        # 把起始短语编码成数字列表
        context = torch.tensor([encode(prompt)], dtype=torch.long)

        # 自回归生成 80 个新字
        output = model.generate(context, max_new_tokens=80, temperature=temperature)

        # 解码回文本
        text = decode(output[0].tolist())
        print(f"  【{prompt}】{text}\n")


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="微型 GPT — 中文版")
    parser.add_argument(
        "--gen", action="store_true",
        help="只生成不训练（需要已有 mini-gpt-cn.pt）"
    )
    parser.add_argument(
        "--temp", type=float, default=0.8,
        help="温度参数：<1 保守，>1 奔放（默认 0.8）"
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="自定义训练文本的路径（TXT 文件，UTF-8 编码）"
    )
    args = parser.parse_args()

    # ---- 1. 加载数据 ----
    text = load_data(args.file)

    # ---- 2. 构建分词器 ----
    encode, decode, vocab_size = build_tokenizer(text)

    # ---- 3. 准备训练/验证数据 ----
    train_data, val_data = prepare_data(encode, text)

    # ---- 4. 创建模型 ----
    model = MiniGPT(vocab_size)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"   模型参数: {total_params:,}")
    # 约 3-4 百万参数。GPT-3 是 1750 亿，GPT-4 约 1.7 万亿。
    # 这个小模型只有它们的一百万分之一——但架构完全一样。

    # ---- 生成模式：加载已有模型直接生成 ----
    if args.gen:
        try:
            model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
            print(f"   ✅ 加载模型: {MODEL_PATH}")
        except FileNotFoundError:
            print(f"   ❌ 未找到 {MODEL_PATH}，请先运行训练：uv run train.py")
            return
        model.eval()
        generate(model, encode, decode, temperature=args.temp)
        return

    # ---- 训练模式：训练 + 保存 + 生成 ----
    model = train(model, train_data, val_data)

    # 保存模型——下次可以直接 --gen 加载
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"💾 模型保存到 {MODEL_PATH}")

    # 训练完了，生成一些示例看看效果
    model.eval()
    generate(model, encode, decode, temperature=args.temp)


if __name__ == "__main__":
    main()
