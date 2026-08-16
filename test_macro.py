import asyncio
from services.macro_engine import get_macro_data, generate_macro_analysis

async def run_test():
    print("Test 1: yfinance orqali makro ma'lumotlarni tortish...")
    spx, dxy, us10y = get_macro_data()
    print(f"Natija -> SPX: {spx}, DXY: {dxy}, US10Y: {us10y}")
    
    if spx is not None:
        print("\nTest 2: Gemini orqali Makro Tahlilni shakllantirish...")
        analysis = await generate_macro_analysis(spx, dxy, us10y)
        print("======== Tahlil Natijasi ========")
        print(analysis)
        print("=================================")
    else:
        print("Xatolik: Ma'lumotlar kelmadi!")

if __name__ == "__main__":
    asyncio.run(run_test())
