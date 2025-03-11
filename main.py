import os
import logging
import asyncio
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
import aiohttp

# 加载环境变量
load_dotenv()

# 配置日志
def setup_logging():
    # 创建logs目录
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 设置日志文件名（包含日期）
    log_filename = f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log'
    
    # 配置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# 初始化机器人
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# API endpoints
PRICE_API = "https://www.vip-license.com/v1/price"
PAY_RESULT_API = "https://www.vip-license.com/vip/pay/result"
LICENSE_API = "http://www.vip-license.com/v1/license/veisher"

# 主菜单按钮
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 查询EA价格", callback_data="check_price"))
    builder.add(InlineKeyboardButton(text="🔑 License管理", callback_data="manage_license"))
    builder.adjust(1)
    return builder.as_markup()

# 启动命令处理
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"用户 {username}({user_id}) 启动了机器人")
    
    try:
        await message.answer(
            "欢迎使用EA策略授权管理机器人！\n"
            "请选择以下功能：",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"成功向用户 {username}({user_id}) 发送主菜单")
    except Exception as e:
        logger.error(f"向用户 {username}({user_id}) 发送主菜单失败: {str(e)}")
        raise

# 价格查询回调处理
@dp.callback_query(lambda c: c.data == "check_price")
async def process_check_price(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    logger.info(f"用户 {username}({user_id}) 点击了价格查询按钮")
    
    try:
        await callback_query.message.answer(
            "请输入EA策略号（例如：NO-75）：",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="返回主菜单", callback_data="main_menu")]
            ])
        )
        logger.info(f"成功向用户 {username}({user_id}) 发送策略号输入提示")
    except Exception as e:
        logger.error(f"向用户 {username}({user_id}) 发送策略号输入提示失败: {str(e)}")
        raise
    finally:
        await callback_query.answer()

# 处理策略号输入
@dp.message()
async def handle_strategy_input(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    strategy_id = message.text.strip()
    
    logger.info(f"用户 {username}({user_id}) 输入了策略号: {strategy_id}")
    
    if not strategy_id.startswith("NO-"):
        logger.warning(f"用户 {username}({user_id}) 输入了错误格式的策略号: {strategy_id}")
        await message.answer("请输入正确的策略号格式（例如：NO-75）")
        return

    try:
        # 异步请求价格
        async with aiohttp.ClientSession() as session:
            logger.info(f"正在查询策略 {strategy_id} 的价格信息")
            async with session.get(f"{PRICE_API}?strategy={strategy_id}") as response:
                if response.status == 200:
                    price_data = await response.json()
                    price = price_data.get("price", "未知")
                    logger.info(f"成功获取策略 {strategy_id} 的价格: {price}")
                    
                    # 创建支付按钮
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="立即支付", callback_data=f"pay_{strategy_id}")],
                        [InlineKeyboardButton(text="返回主菜单", callback_data="main_menu")]
                    ])
                    
                    await message.answer(
                        f"策略号：{strategy_id}\n"
                        f"价格：${price}",
                        reply_markup=keyboard
                    )
                    logger.info(f"成功向用户 {username}({user_id}) 发送价格信息")
                else:
                    error_msg = f"获取价格信息失败，状态码: {response.status}"
                    logger.error(error_msg)
                    await message.answer("获取价格信息失败，请稍后重试。")
    except Exception as e:
        error_msg = f"处理策略号 {strategy_id} 时发生错误: {str(e)}"
        logger.error(error_msg)
        await message.answer("处理请求时发生错误，请稍后重试。")

# License管理回调处理
@dp.callback_query(lambda c: c.data == "manage_license")
async def process_manage_license(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    logger.info(f"用户 {username}({user_id}) 点击了License管理按钮")
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"正在获取用户 {username}({user_id}) 的License信息")
            async with session.get(LICENSE_API) as response:
                if response.status == 200:
                    licenses = await response.json()
                    logger.info(f"成功获取用户 {username}({user_id}) 的License信息: {json.dumps(licenses, ensure_ascii=False)}")
                    
                    if licenses:
                        license_text = "您的License列表：\n\n"
                        for license in licenses:
                            license_text += f"策略号：{license['strategy_id']}\n"
                            license_text += f"激活码：{license['activation_code']}\n"
                            license_text += "---------------\n"
                    else:
                        license_text = "您还没有购买任何License。"
                else:
                    error_msg = f"获取License信息失败，状态码: {response.status}"
                    logger.error(error_msg)
                    license_text = "获取License信息失败，请稍后重试。"
        
        await callback_query.message.answer(
            license_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="返回主菜单", callback_data="main_menu")]
            ])
        )
        logger.info(f"成功向用户 {username}({user_id}) 发送License信息")
    except Exception as e:
        error_msg = f"处理License管理请求时发生错误: {str(e)}"
        logger.error(error_msg)
        await callback_query.message.answer("处理请求时发生错误，请稍后重试。")
    finally:
        await callback_query.answer()

# 返回主菜单回调处理
@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    logger.info(f"用户 {username}({user_id}) 点击了返回主菜单按钮")
    
    try:
        await callback_query.message.edit_text(
            "请选择以下功能：",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"成功向用户 {username}({user_id}) 显示主菜单")
    except Exception as e:
        logger.error(f"向用户 {username}({user_id}) 显示主菜单失败: {str(e)}")
        raise
    finally:
        await callback_query.answer()

# 支付处理
@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def process_payment(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    strategy_id = callback_query.data.split("_")[1]
    
    logger.info(f"用户 {username}({user_id}) 开始支付策略 {strategy_id}")
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"正在处理用户 {username}({user_id}) 的支付请求")
            async with session.post(
                PAY_RESULT_API,
                json={"strategy_id": strategy_id, "status": "success"}
            ) as response:
                if response.status == 200:
                    logger.info(f"用户 {username}({user_id}) 支付成功")
                    await callback_query.message.answer("支付成功！")
                else:
                    error_msg = f"支付失败，状态码: {response.status}"
                    logger.error(error_msg)
                    await callback_query.message.answer("支付失败，请稍后重试。")
    except Exception as e:
        error_msg = f"处理支付请求时发生错误: {str(e)}"
        logger.error(error_msg)
        await callback_query.message.answer("处理支付请求时发生错误，请稍后重试。")
    finally:
        await callback_query.answer()

# 启动机器人
async def main():
    logger.info("机器人启动中...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"机器人启动失败: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 