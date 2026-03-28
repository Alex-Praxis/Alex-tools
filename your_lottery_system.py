import random
import json
import os
import math
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from datetime import date  # 用于获取当前日期


SAVE_FILE = 'game_state.json'

# 初始化变量
prize_pool = []  # 奖池中的奖品列表
total_won_value = 0  # 已抽取奖品的总价值
total_pool_value = 3000  # 总奖池价值
draws_per_day = 8  # 平均每天抽奖次数
prize_id_counter = 1  # 奖品编号计数器
letter_counter = 0  # 字母计数器
draw_history = []  # 抽奖历史记录
consolation_rewards = []  # 安慰奖列表


# 使用对数缩放公式计算概率，考虑碎片数量
def calculate_probability(prize_value, limit_value, remaining_fragments, total_fragments):
    # 计算奖品的剩余总价值
    remaining_value = prize_value * (remaining_fragments / total_fragments)

    # 期望值
    expected_value = get_expected_draw_value()

    # 对数缩放公式，考虑剩余碎片
    return math.log(expected_value / remaining_value + 1)

# 生成编号，使用字母加数字的组合，例如 A1, B2, C3 等
def generate_prize_id():
    global prize_id_counter, letter_counter
    letter = chr(65 + letter_counter)  # 从 'A' 开始，递增字母
    prize_id = f"{letter}{prize_id_counter}"
    prize_id_counter += 1
    if prize_id_counter > 99:  # 达到一定数量后，字母变动
        prize_id_counter = 1
        letter_counter += 1
    return prize_id


# 计算单次抽奖的期望价值
def get_expected_draw_value():
    return total_pool_value / (30 * draws_per_day)


# 批量交互输入奖品
def add_prizes_interactive():
    print("请输入奖品信息，每个奖品格式为 '名称,价值,数量'，用空格分隔不同奖品，输入 'done' 完成:")
    while True:
        prizes_input = input("批量输入奖品: ")
        if prizes_input.lower() == 'done':
            break
        prizes_list = prizes_input.split()
        for prize in prizes_list:
            try:
                prize_name, prize_value, limit_value = prize.split(',')
                prize_value = int(prize_value)
                limit_value = int(limit_value)  # 这是奖品的数量

                if check_prize_name_exists(prize_name):
                    print(f"输入错误：奖品名称 '{prize_name}' 已经存在，请重新输入。")
                else:
                    add_prize(prize_name, prize_value, limit_value)
            except ValueError:
                print(f"输入格式有误: {prize}")


# 检查奖品名称是否已存在
def check_prize_name_exists(prize_name):
    for prize in prize_pool:
        if prize_name == prize['name']:
            return True
    return False


# 添加奖品的核心逻辑
def add_prize(prize_name, prize_value, limit_value):
    fragments = decide_fragments(prize_value)  # 根据价值决定碎片数量
    fragment_value = prize_value / fragments  # 将奖品价值均分为多个碎片
    prize_pool.append({
        'id': generate_prize_id(),  # 生成唯一编号
        'name': prize_name,
        'total_value': prize_value,  # 奖品总价值
        'fragment_value': fragment_value,  # 每个碎片价值
        'total_fragments': fragments,  # 总碎片数
        'remaining_fragments': fragments,  # 剩余碎片数
        'limit_value': limit_value,  # 奖品的数量
        'probability': 0,  # 初始化概率
        'cooldown': 0  # 冷却机制，初始为0
    })
    update_probabilities()
    save_game_state()


# 动态决定碎片数
def decide_fragments(total_value):
    if total_value <= 100:
        return 1  # 不拆分
    elif total_value <= 500:
        return 2  # 拆分为 2
    elif total_value <= 2000:
        return 4  # 拆分为 4
    else:
        return 8  # 拆分为 8


# 更新所有奖品的概率
def update_probabilities():
    global total_pool_value, draws_per_day, total_won_value

    # 计算单次抽奖的期望值
    expected_value = get_expected_draw_value()

    total_probability = 0  # 用于累计所有奖品的总概率
    max_probability = 0.3  # 设置每个奖品的最大抽中概率上限

    for prize in prize_pool:
        # 计算基础概率，包含剩余碎片和总碎片的影响
        base_probability = calculate_probability(
            prize['total_value'],
            prize['limit_value'],
            prize['remaining_fragments'],
            prize['total_fragments']
        )

        # 应用冷却机制
        if prize['cooldown'] > 0:
            prize['cooldown'] = max(0, prize['cooldown'] - 0.01)
            adjusted_probability = base_probability * (1 - prize['cooldown'])
        else:
            adjusted_probability = base_probability

        # 确保每个奖品的概率不会超过最大值
        prize['probability'] = min(adjusted_probability, max_probability)

        total_probability += prize['probability']

    # 如果支出接近总池金额的80%，减少高价值奖品的概率
    if total_won_value > total_pool_value * 0.8:
        for prize in prize_pool:
            if prize['total_value'] > expected_value * 5:
                prize['probability'] *= 0.5  # 减少高价值奖品概率

    # 未中奖的概率 = 1 - 所有奖品概率之和
    no_win_probability = 1 - total_probability
    return max(0, no_win_probability)  # 保证未中奖概率不小于0

# 抽奖逻辑
def player_draw():
    global total_won_value, prize_pool
    if not prize_pool:
        return "奖池中没有奖品了。"

    # 生成 0 到 1 之间的随机数
    rand_value = random.uniform(0, 1)


    # 如果随机值小于 0.5，直接发放安慰奖
    if rand_value < 0.618:
        return give_consolation_reward()

    # 否则进入奖品随机抽奖逻辑
    cumulative_probabilities = []
    current_sum = 0

    # 更新概率并返回未中奖的概率
    update_probabilities()

    # 计算累积概率
    for prize in prize_pool:
        current_sum += prize['probability']
        cumulative_probabilities.append((prize, current_sum))

    # 调整 rand_value 到 [0, 总的累积概率] 范围内
    rand_value = random.uniform(0, current_sum)

    # 检查是否中奖
    for prize, cumulative_probability in cumulative_probabilities:
        if rand_value <= cumulative_probability and prize['remaining_fragments'] > 0:
            prize['remaining_fragments'] -= 1  # 减少碎片数
            total_won_value += prize['fragment_value']  # 增加抽中奖品的价值

            # 冷却机制：抽中后奖品概率降低
            prize['cooldown'] = 0.2  # 冷却减少该奖品的中奖概率

            draw_history.append({
                "result": "中奖",
                "prize": prize['name'],
                "fragment_won": prize['total_fragments'] - prize['remaining_fragments'],
                "total_fragments": prize['total_fragments'],
                "value": prize['fragment_value'],
                "date": date.today().strftime("%Y-%m-%d")
            })

            # 如果奖品的所有碎片都抽完了，减少该奖品的 limit_value
            if prize['remaining_fragments'] == 0:
                prize['limit_value'] -= 1
                if prize['limit_value'] > 0:
                    prize['remaining_fragments'] = prize['total_fragments']  # 重置为完整碎片数
                else:
                    prize_pool.remove(prize)  # 如果所有数量都用完，移除该奖品

            update_probabilities()  # 更新概率
            save_game_state()  # 保存状态
            return f"您抽中了 {prize['name']} 的一个碎片！已抽中 {prize['total_fragments'] - prize['remaining_fragments']} / {prize['total_fragments']} 碎片。"

    # 如果到达这里，表示没有命中任何奖品，返回安慰奖
    return give_consolation_reward()

# 从安慰奖列表中随机选择一个
def give_consolation_reward():
    if not consolation_rewards:
        return "未中奖，当前没有设定安慰奖。"
    reward = random.choice(consolation_rewards)
    draw_history.append({
        "result": "未中奖",
        "consolation_reward": reward,
        "date": date.today().strftime("%Y-%m-%d")
    })
    save_game_state()
    return f"未中奖，安慰奖：{reward}"


# 保存游戏状态
def save_game_state():
    game_state = {
        'prize_pool': prize_pool,
        'total_won_value': total_won_value,
        'total_pool_value': total_pool_value,
        'draws_per_day': draws_per_day,
        'prize_id_counter': prize_id_counter,
        'letter_counter': letter_counter,
        'draw_history': draw_history,
        'consolation_rewards': consolation_rewards  # 保存安慰奖列表
    }
    with open(SAVE_FILE, 'w') as file:
        json.dump(game_state, file)

# 加载游戏状态
def load_game_state():
    global prize_pool, total_won_value, total_pool_value, draws_per_day, prize_id_counter, letter_counter, draw_history, consolation_rewards
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as file:
            try:
                game_state = json.load(file)
                prize_pool = game_state.get('prize_pool', [])
                total_won_value = game_state.get('total_won_value', 0)
                total_pool_value = game_state.get('total_pool_value', 3000)
                draws_per_day = game_state.get('draws_per_day', 8)
                prize_id_counter = game_state.get('prize_id_counter', 1)
                letter_counter = game_state.get('letter_counter', 0)
                draw_history = game_state.get('draw_history', [])
                consolation_rewards = game_state.get('consolation_rewards', [])

                # 校验是否有必要的字段, 初始化 fragment 值
                for prize in prize_pool:
                    if 'fragment_value' not in prize:
                        prize['fragment_value'] = prize['total_value'] / prize['total_fragments']
                    if 'remaining_fragments' not in prize:
                        prize['remaining_fragments'] = prize['total_fragments']
                update_probabilities()

            except json.JSONDecodeError:
                print(f"无法加载文件 {SAVE_FILE}，文件可能为空或格式损坏。正在初始化游戏状态...")
                initialize_game_state()  # 如果解析失败，初始化状态
    else:
        print(f"未找到游戏状态文件 {SAVE_FILE}，正在初始化...")
        initialize_game_state()


# 初始化游戏状态并保存到文件
def initialize_game_state():
    global prize_pool, total_won_value, total_pool_value, draws_per_day, prize_id_counter, letter_counter, draw_history, consolation_rewards
    prize_pool = []
    total_won_value = 0
    total_pool_value = 3000
    draws_per_day = 8
    prize_id_counter = 1
    letter_counter = 0
    draw_history = []
    consolation_rewards = []
    save_game_state()  # 保存初始化后的状态

# 修改奖品的名称、价值和数量
def modify_prize(prize_id):
    prize_to_modify = next((p for p in prize_pool if p['id'] == prize_id), None)

    if prize_to_modify:
        new_name = input(f"输入新的奖品名称 (当前: {prize_to_modify['name']}): ")
        new_value = int(input(f"输入新的奖品价值 (当前: {prize_to_modify['total_value']} RMB): "))
        new_fragments = int(input(f"输入新的碎片数量 (当前: {prize_to_modify['total_fragments']}): "))
        limit_value = int(input(f"输入新的奖品数量 (当前: {prize_to_modify['limit_value']}): "))
        prize_to_modify.update({
            'name': new_name,
            'total_value': new_value,
            'total_fragments': new_fragments,
            'fragment_value': new_value / new_fragments,
            'remaining_fragments': new_fragments,
            'limit_value': limit_value
        })
        update_probabilities()
        save_game_state()
        return f"奖品 {new_name} 修改成功！"
    return f"未找到编号为 {prize_id} 的奖品。"

# 查看奖池函数
def view_prizes():
    if not prize_pool:
        return "奖池中没有奖品。"

    prize_info = []
    for prize in prize_pool:
        probability = prize['probability']
        prize_info.append(
            f"编号: {prize['id']} - {prize['name']} - 价值: {prize['total_value']} RMB, 概率: {probability:.2%}, "
            f"剩余碎片: {prize['remaining_fragments']} / {prize['total_fragments']}"
        )

    # 返回文本形式的奖池信息
    return "\n".join(prize_info)

# 设置支持中文的字体路径
font_path = '/System/Library/Fonts/PingFang.ttc'
prop = fm.FontProperties(fname=font_path)

# 显示奖品概率的图形化展示
def show_probability_chart():
    # 提取奖品名称和概率
    prize_names = [prize['name'] for prize in prize_pool]
    probabilities = [prize['probability'] for prize in prize_pool]

    # 设置图形大小
    plt.figure(figsize=(8, 6))

    # 绘制柱状图
    plt.barh(prize_names, probabilities, color='skyblue')

    # 设置标题和轴标签
    plt.title('奖品中奖概率分布', fontsize=14, fontproperties=prop)
    plt.ylabel('奖品名称', fontsize=6, fontproperties=prop)
    plt.xlabel('中奖概率', fontsize=12, fontproperties=prop)

    # 设置 y 轴标签（奖品名称）的字体
    plt.yticks(range(len(prize_names)), prize_names, fontproperties=prop)

    # 显示百分比格式
    plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2%}'))

    # 显示图形
    plt.tight_layout()
    plt.show()


# 查看抽奖历史
def view_draw_history():
    if not draw_history:
        return "没有抽奖历史。"
    return "\n".join(
        [f"{entry['date']} - {entry['result']}: {entry.get('prize', '无')} - {entry.get('consolation_reward', '')}" for
         entry in draw_history])


# 查看已抽取奖品的总价值
def view_won_prize_total():
    return f"已抽取奖品总价值: {total_won_value} RMB"


# 查看用户拥有的碎片
def view_fragments():
    fragment_info = [
        f"{prize['name']} - 已拥有 {prize['total_fragments'] - prize['remaining_fragments']} / {prize['total_fragments']} 碎片"
        for prize in prize_pool if prize['remaining_fragments'] < prize['total_fragments']]
    return "\n".join(fragment_info) if fragment_info else "您没有任何碎片。"


# 查看安慰奖
def view_consolation_rewards():
    return "\n".join([f"{idx + 1}. {reward}" for idx, reward in
                      enumerate(consolation_rewards)]) if consolation_rewards else "当前没有设定任何安慰奖。"


# 添加安慰奖
def add_consolation_rewards():
    print("请输入安慰奖，每个奖励格式为 '奖励内容'，输入 'done' 完成:")
    while True:
        reward_input = input("输入安慰奖 (例: 做一次瑜伽): ").strip()

        if reward_input.lower() == 'done':
            break

        if reward_input in consolation_rewards:
            print(f"安慰奖 '{reward_input}' 已经存在，请输入其他内容。")
        else:
            consolation_rewards.append(reward_input)
            print(f"安慰奖 '{reward_input}' 已添加。")

    print("安慰奖设置完毕。")
    save_game_state()  # 保存状态

# 修改安慰奖
def modify_consolation_reward():
    # 先查看当前的安慰奖列表
    print(view_consolation_rewards())
    if not consolation_rewards:
        return "没有安慰奖可修改。"

    try:
        # 让用户选择要修改的安慰奖编号
        choice = int(input("请输入要修改的安慰奖编号: ")) - 1
        if 0 <= choice < len(consolation_rewards):
            # 输入新的安慰奖内容
            new_reward = input(f"请输入新的安慰奖内容 (当前: {consolation_rewards[choice]}): ")
            consolation_rewards[choice] = new_reward  # 修改安慰奖
            save_game_state()  # 保存游戏状态
            return f"安慰奖已更新为 '{new_reward}'。"
        else:
            return "无效的编号，请输入有效的安慰奖编号。"
    except ValueError:
        return "输入有误，请输入数字。"

# 删除安慰奖
def remove_consolation_reward():
    print(view_consolation_rewards())
    if not consolation_rewards:
        return "没有安慰奖可删除。"
    try:
        choice = int(input("请输入要删除的安慰奖编号: ")) - 1
        if 0 <= choice < len(consolation_rewards):
            removed_reward = consolation_rewards.pop(choice)
            save_game_state()
            return f"安慰奖 '{removed_reward}' 已被删除。"
        else:
            return "无效的编号，请输入有效的安慰奖编号。"
    except ValueError:
        return "输入有误，请输入数字。"


# 奖品管理菜单
def prize_management_menu():
    while True:
        print("\n===================== 奖品管理 =====================")
        print("1. 添加奖品")
        print("2. 修改奖品")
        print("3. 删除奖品")
        print("4. 查看当前奖池及概率分布图")
        print("5. 返回主菜单")
        choice = input("请输入选择 (1-5): ")

        if choice == "1":
            print(view_prizes())
            add_prizes_interactive()

        elif choice == "2":
            print(view_prizes())
            prize_id = input("请输入要修改的奖品编号（输入 'q' 或 'exit' 退出修改操作）: ").strip()
            if prize_id.lower() in ['q', 'exit']:
                print("已退出修改操作。")
            else:
                print(modify_prize(prize_id))

        elif choice == "3":
            print(view_prizes())
            print(remove_prizes())

        elif choice == "4":
            print("\n当前奖池信息：")
            print(view_prizes())  # 先打印奖池的文本信息
            show_probability_chart()  # 再显示概率图表
        elif choice == "5":
            break
        else:
            print("无效选择，请重新输入。")


# 主菜单
def main_menu():
    global total_pool_value
    load_game_state()
    while True:
        print("\n===================== 抽奖系统 =====================")
        print(f"当前总奖池价值: {total_pool_value} RMB")
        print(f"已抽取奖品总价值: {total_won_value} RMB")
        print(f"平均每天抽奖次数: {draws_per_day}")
        print("--------------------------------------------------")
        print("奖池中的奖品（编号: 名称 - 剩余碎片/总碎片）：")
        for prize in prize_pool:
            print(f"- {prize['id']}: {prize['name']} - {prize['remaining_fragments']}/{prize['total_fragments']} 碎片")
        print("\n===================== 操作选项 =====================")
        print("1. 奖品管理")
        print("2. 安慰奖管理")
        print("3. 查看数据")
        print("4. 抽奖")
        print("5. 系统设置")
        print("6. 退出")
        choice = input("请输入选择 (1-6): ")
        if choice == "1":
            prize_management_menu()
        elif choice == "2":
            consolation_reward_management_menu()
        elif choice == "3":
            view_data_menu()
        elif choice == "4":
            print(player_draw())
        elif choice == "5":
            system_settings_menu()  # 修复调用系统设置
        elif choice == "6":
            print("退出程序，保存状态。")
            save_game_state()
            break
        else:
            print("无效选择，请重新输入。")

# 查看数据菜单
def view_data_menu():
    while True:
        print("\n===================== 查看数据 =====================")
        print("1. 查看抽奖历史")
        print("2. 查看已抽取奖品总额")
        print("3. 查看我的碎片")
        print("4. 返回主菜单")
        choice = input("请输入选择 (1-4): ")

        if choice == "1":
            print(view_draw_history())  # 调用查看抽奖历史的函数
        elif choice == "2":
            print(view_won_prize_total())  # 调用查看已抽取奖品总价值的函数
        elif choice == "3":
            print(view_fragments())  # 调用查看用户拥有的碎片的函数
        elif choice == "4":
            break  # 返回主菜单
        else:
            print("无效选择，请重新输入。")

# 安慰奖管理菜单
def consolation_reward_management_menu():
    while True:
        print("\n================== 安慰奖管理 ==================")
        print("1. 添加安慰奖")
        print("2. 修改安慰奖")
        print("3. 删除安慰奖")
        print("4. 查看安慰奖")
        print("5. 返回主菜单")
        choice = input("请输入选择 (1-5): ")

        if choice == "1":
            add_consolation_rewards()  # 调用添加安慰奖函数
        elif choice == "2":
            print(modify_consolation_reward())  # 调用修改安慰奖函数
        elif choice == "3":
            print(remove_consolation_reward())  # 调用删除安慰奖函数
        elif choice == "4":
            print(view_consolation_rewards())  # 调用查看安慰奖函数
        elif choice == "5":
            break  # 返回主菜单
        else:
            print("无效选择，请重新输入。")

# 系统设置菜单
def system_settings_menu():
    while True:
        print("\n==================== 系统设置 ======================")
        print("1. 修改每月奖池总价值(= 每月打算花多少钱给自己各种奖励?)")
        print("2. 修改平均每天抽奖次数")
        print("3. 返回主菜单")
        choice = input("请输入选择 (1-3): ")

        if choice == "1":
            try:
                new_value = int(input("输入新的总奖池价值 (RMB): "))
                global total_pool_value
                total_pool_value = new_value
                update_probabilities()
                save_game_state()
            except ValueError:
                print("输入有误，请输入数字。")

        elif choice == "2":
            try:
                new_value = int(input("输入新的平均每天抽奖次数: "))
                global draws_per_day
                draws_per_day = new_value
                save_game_state()
            except ValueError:
                print("输入有误，请输入数字。")

        elif choice == "3":
            break

        else:
            print("无效选择，请重新输入。")


# 程序入口
if __name__ == "__main__":
    main_menu()