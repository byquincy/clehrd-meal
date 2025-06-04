import requests
from bs4 import BeautifulSoup, Tag
import json
import datetime

import time

# CONSTANTS
POST_URL = "https://hs.clehrd.or.kr/kr/html/sub02/0204.html?"
JSON_FILE = "clehrd_meals.json"
WEEK_NO_FILE = "WEEK_NO"
KST = datetime.timezone(datetime.timedelta(hours=9))
CLEANING_CUTOFF = 30
INDEX2PERIOD_STR = ["아침", "점심", "저녁"]

# functions
def text2date(date_text:str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(date_text, "%Y-%m-%d")
    except:
        return datetime.datetime.fromtimestamp(0)

def date2str(date:datetime.datetime|datetime.date) -> str:
    return date.strftime("%Y-%m-%d")

def mealHtml2list(set:Tag) -> list[str]:
    menu = set.select("ul > li")
    return [x.text for x in menu]

def getWeeklyMeals(week_no:int) -> dict[str, list[str]]:
    """getWeeklyMeals
    본 함수는 오름차순으로 정렬된 데이터 반환을 보장함.
    """
    response = requests.post(POST_URL, data={"mng_no": week_no})
    soup = BeautifulSoup(response.text.replace("\r", ""), 'html.parser')

    table = soup.select_one("#txt > div.carte_w > div.scl_x > table")

    if table == None:
        return {}
    
    date_list = table.select("thead > tr:nth-child(2) > th")
    if date_list[0].text == '':
        return {}

    meals = [[x.text, []] for x in date_list]
    
    for i in range(1, 4):
        meal_row = table.select(f"tbody > tr:nth-child({i}) > td")
        if len(meals) != len(meal_row):
            return {}

        for i in range(len(meals)):
            meals[i][1].append(mealHtml2list(meal_row[i]))
    
    return dict(meals)

def sortDict(dict2sort:dict) -> dict:
    return dict(sorted(dict2sort.items()))

class MealFile:
    def __init__(self, file_name:str=JSON_FILE, cleaning_cutoff=CLEANING_CUTOFF) -> None:
        self.file_name = file_name
        self.cleaning_cutoff = cleaning_cutoff
        try:
            with open(self.file_name, "r", encoding="utf8") as f:
                self.meals:dict = json.load(f)
        except:
            self.meals:dict = {}
        self.cleanAndWrite()
    
    def __str__(self) -> str:
        return self.meal_dict2str(self.meals)
    
    def meal_dict2str(self, dict4str:dict) -> str:
        return "\n".join([self.day_meals2str(key, value) for key, value in dict4str.items()])

    def day_meals2str(self, day:str, meal_list:list[list]) -> str:
        result = f"{day}:\n"
        for i, meal in enumerate(meal_list):
            result += f"   {INDEX2PERIOD_STR[i]}\n"
            for menu in meal:
                result += f"    - {menu}\n"
        
        return result

    def update(self, meals2update:dict) -> 'MealFile':
        """update
        meals2update:dict - 정렬 상태는 상관 없음.
        self.meal_file은 반드시 정렬 상태여야 합니다.
        """
        if not meals2update:
            return self

        meals2update = sortDict(meals2update)
        first_update_key = list(meals2update.keys())[0]

        if (not self.meals) or (first_update_key > list(self.meals.keys())[-1]):
            self.meals.update(meals2update)
        else:
            new_meals:dict = {}
            for key, value in self.meals.items():
                if first_update_key < key:
                    new_meals.update(meals2update)
                new_meals[key] = value
            self.meals = new_meals
        
        self.cleanAndWrite()
        return self
    
    def sort(self) -> 'MealFile':
        """sort
        가급적 사용하지 않는 것을 권장합니다.
        리스트의 정렬을 보장할 수 없을 때, 리스트를 전부 다시 정렬합니다.
        """
        self.meals = sortDict(self.meals)
        self.cleanAndWrite()
        return self
    
    def cleanAndWrite(self, cleaning_cutoff:int|None=None) -> 'MealFile':
        """cleanAndWrite
        cleaning_cutoff에 맞춰 리스트를 정리한 후, 파일을 씁니다.
        """
        if cleaning_cutoff == None:
            cleaning_cutoff = self.cleaning_cutoff

        since = date2str(
            datetime.datetime.now(tz=KST).date()
            - datetime.timedelta(days=cleaning_cutoff)
            )
        for key in list(self.meals.keys()):
            if key < since:
                del self.meals[key]
            else:
                break

        self.write()
        return self

    def write(self) -> 'MealFile':
        with open(self.file_name, "w", encoding="utf-8") as f:
            json.dump(self.meals, f)
        return self

    def getSince(self, since_date:datetime.date):
        result = {}
        since_str = date2str(since_date)
        is_after = False
        for key, value in self.meals.items():
            if is_after or (is_after := key >= since_str):
                result[key] = value
        
        return result

class WeekNo:
    def __init__(self, file_name:str=WEEK_NO_FILE, week_int:int|None=None) -> None:
        self.file_name = file_name

        if week_int == None:
            try:
                with open(self.file_name, "rb") as f:
                    self.week_int = int.from_bytes(f.read())
            except:
                self.week_int = 219
                self.write()
        else:
            self.week_int = week_int
            self.write()
        
        print(self)
    
    def __str__(self) -> str:
        return f"WeekNo: {self.week_int}"

    def plus(self, no:int=1) -> int:
        self.week_int += no
        self.write()
        print("Plus:", self)
        return self.week_int
    
    def minus(self, no:int=1) -> int:
        self.week_int -= no
        self.write()
        print("Minus:", self)
        return self.week_int

    def write(self) -> 'WeekNo':
        with open(self.file_name, "wb") as f:
            f.write(self.week_int.to_bytes())
        
        return self

meal:MealFile = MealFile()
class DataSync:
    def __init__(self, meal:MealFile=meal) -> None:
        self.meal:MealFile = meal
        self.week_no:WeekNo = WeekNo()
    
    def sync(self) -> 'DataSync':
        print("Sync starts")
        self.meal.update(self.checkNewData())
        return self
    
    def checkNewData(self) -> dict:
        result:dict = {}
        while weekly_meals:=getWeeklyMeals(self.week_no.plus()):
            print("checkNewData")
            result.update(weekly_meals)
        self.week_no.minus()

        return result
data_syncer:DataSync = DataSync()

# main
if __name__ == "__main__":
    print(
        MealFile()
            .update(getWeeklyMeals(220))
            .update(getWeeklyMeals(221))
    )