import requests
import csv
import time


def get_transaction_type(data):
    info = data.get("webengage", {})

    cat2 = info.get("cat_2", "")
    category = info.get("category", "")
    credit = info.get("credit", 0) or 0
    rent = info.get("rent", 0) or 0

    if cat2 == "temporary-rent":
        return "اجاره کوتاه‌مدت"

    if "sell" in cat2 or "sell" in category:
        return "فروش"

    if "rent" in cat2 or "rent" in category:
        if credit > 0 and rent == 0:
            return "رهن کامل"

        if credit > 0 and rent > 0:
            return "رهن و اجاره"

        if credit == 0 and rent > 0:
            return "اجاره"

    return "نامشخص"


def check_agency(data):
    title = data.get("seo", {}).get("web_info", {}).get("title", "")
    description = ""

    for section in data.get("sections", []):
        if section.get("section_name") == "DESCRIPTION":
            for widget in section.get("widgets", []):
                if widget.get("widget_type") == "DESCRIPTION_ROW":
                    description = widget.get("data", {}).get("text", "")

    text = (title + " " + description).lower()
    title_text = title.lower()

    # این عبارت‌ها نشانه املاکی بودن نیستند
    personal_phrases = [
        "املاک تماس نگیرد",
        "املاکی تماس نگیرد",
        "مشاور املاک تماس نگیرد",
        "مشاورین املاک تماس نگیرند",
        "همکاری با املاک ندارم",
        "همکاری با مشاورین املاک ندارم",
        "املاک پاسخگو نیستم",
    ]

    for phrase in personal_phrases:
        text = text.replace(phrase, "")
        title_text = title_text.replace(phrase, "")

    # مثل: "مناسب برای دفتر املاک"
    if "مناسب" in title_text:
        title_text = title_text.replace("دفتر املاک", "")
        title_text = title_text.replace("دفتراملاک", "")

    # نشانه‌های واضح املاکی بودن در عنوان
    if (
        "املاک" in title_text
        or "فایل دیگر" in title_text
        or "مشاوردرخریدوفروش" in title_text
        or "مشاور در خرید و فروش" in title_text
    ):
        return True, "نشانه املاکی در عنوان", description

    agency_signals = {
        "کد فایل": 3,
        "دفتر املاک": 3,
        "مشاور املاک": 3,
        "کارشناس فروش": 2,
        "کارشناس ملک": 2,
        "فایلینگ": 2,
        "فایل مشابه": 1,
        "جهت بازدید": 1,
        "مشاور": 1,
    }

    score = 0
    reasons = []

    for phrase, points in agency_signals.items():
        if phrase in text:

            # مثلاً: "مناسب برای ... دفتر املاک"
            if phrase == "دفتر املاک":
                index = text.find("دفتر املاک")
                before = text[max(0, index - 100):index]

                if "مناسب" in before:
                    continue

            score += points
            reasons.append(phrase)

    return score >= 2, "، ".join(reasons), description


# گرفتن لیست آگهی‌ها
search_url = "https://api.divar.ir/v8/postlist/w/search"

payload = {
    "city_ids": ["746"],
    "search_data": {
        "form_data": {
            "data": {
                "business-type": {
                    "repeated_string": {
                        "value": ["personal"]
                    }
                },
                "category": {
                    "str": {
                        "value": "real-estate"
                    }
                }
            }
        },
        "server_payload": {
            "@type": "type.googleapis.com/widgets.SearchData.ServerPayload",
            "additional_form_data": {
                "data": {
                    "sort": {
                        "str": {
                            "value": "sort_date"
                        }
                    }
                }
            }
        }
    }
}


tokens = []
seen_tokens = set()

pagination_data = None
page_number = 1


while True:

    if pagination_data:
        payload["pagination_data"] = pagination_data

    response = requests.post(search_url, json=payload)

    print("صفحه", page_number, ":", response.status_code)

    if response.status_code != 200:
        break

    data = response.json()

    new_count = 0

    for item in data.get("list_widgets", []):
        if item.get("widget_type") == "POST_ROW":

            token = item.get("data", {}).get("token")

            if token and token not in seen_tokens:
                tokens.append(token)
                seen_tokens.add(token)
                new_count += 1

    if new_count == 0:
        print("آگهی جدیدی نبود، پایان")
        break

    pagination = data.get("pagination", {})

    if not pagination.get("has_next_page"):
        break

    pagination_data = pagination.get("data")

    if not pagination_data:
        break

    page_number += 1

    time.sleep(0.5)


print("تعداد کل آگهی‌ها:", len(tokens))


# گرفتن اطلاعات هر آگهی
personal_results = []
suspected_results = []


for i, token in enumerate(tokens, start=1):

    url = f"https://api.divar.ir/v8/posts-v2/web/{token}"

    response = None

    # اگر اتصال قطع شد، تا 3 بار دوباره تلاش می‌کند
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=20)
            break

        except requests.exceptions.RequestException as error:
            print(
                f"خطای اتصال برای {token} "
                f"- تلاش {attempt + 1} از 3"
            )
            print(error)

            time.sleep(5)

    # اگر بعد از 3 بار هنوز وصل نشد
    if response is None:
        print("رد شد:", token)
        continue

    # اگر سرور پاسخ موفق نداد
    if response.status_code != 200:
        print(
            "خطای سرور:",
            response.status_code,
            token
        )
        continue

    ad_data = response.json()

    # فقط آگهی شخصی
    if ad_data.get("webengage", {}).get("business_type") != "personal":
        continue

    # فقط لاهیجان
    if (
        ad_data.get("seo", {})
        .get("web_info", {})
        .get("city_persian")
        != "لاهیجان"
    ):
        continue

    transaction_type = get_transaction_type(ad_data)

    # حذف اجاره‌های روزانه / شبانه / کوتاه‌مدت
    if transaction_type == "اجاره کوتاه‌مدت":
        continue

    # حذف مواردی که اصلاً معامله ملکی مشخص نیستند
    if transaction_type == "نامشخص":
        continue

    result = {
        "عنوان": (
            ad_data.get("seo", {})
            .get("web_info", {})
            .get("title")
        ),
        "نوع معامله": transaction_type,
        "محله": (
            ad_data.get("seo", {})
            .get("web_info", {})
            .get("district_persian")
        ),
        "متراژ": None,
        "سال ساخت": None,
        "تعداد اتاق": None,
        "قیمت کل": None,
        "قیمت هر متر": None,
        "طبقه": None,
        "تاریخ انتشار": None,
        "لینک": ad_data.get("share", {}).get("web_url")
    }

    for section in ad_data.get("sections", []):

        # تاریخ انتشار
        if section.get("section_name") == "TITLE":

            for widget in section.get("widgets", []):

                if widget.get("widget_type") == "EXPANDABLE_SECTION":

                    for item in widget["data"].get("widget_list", []):

                        text = item.get("data", {}).get("text", "")

                        if "انتشار آگهی:" in text:
                            result["تاریخ انتشار"] = (
                                text.split("\n")[0]
                                .replace("انتشار آگهی:", "")
                                .strip()
                            )

        # اطلاعات ملک
        if section.get("section_name") == "LIST_DATA":

            for widget in section.get("widgets", []):

                if widget.get("widget_type") == "GROUP_INFO_ROW":

                    for item in widget["data"].get("items", []):

                        title = item.get("title")
                        value = item.get("value")

                        if title == "متراژ":
                            result["متراژ"] = value

                        elif title == "ساخت":
                            result["سال ساخت"] = value

                        elif title == "اتاق":
                            result["تعداد اتاق"] = value

                elif widget.get("widget_type") == "UNEXPANDABLE_ROW":

                    title = widget["data"].get("title")
                    value = widget["data"].get("value")

                    if title in ["قیمت کل", "قیمت کل ملک"]:
                        result["قیمت کل"] = value

                    elif title == "قیمت هر متر":
                        result["قیمت هر متر"] = value

                    elif title == "طبقه":
                        result["طبقه"] = value


    # بررسی مشکوک بودن به املاکی
    is_suspected, reason, description = check_agency(ad_data)

    if is_suspected:

        result["دلیل مشکوک بودن"] = reason
        result["توضیحات"] = description

        suspected_results.append(result)

    else:
        personal_results.append(result)


    print(f"{i} از {len(tokens)} گرفته شد: {token}")

    time.sleep(0.8)


# ستون‌های فایل شخصی
fields = [
    "عنوان",
    "نوع معامله",
    "محله",
    "متراژ",
    "سال ساخت",
    "تعداد اتاق",
    "قیمت کل",
    "قیمت هر متر",
    "طبقه",
    "تاریخ انتشار",
    "لینک"
]


# ستون‌های فایل مشکوک به املاکی
suspected_fields = [
    "عنوان",
    "دلیل مشکوک بودن",
    "توضیحات",
    "نوع معامله",
    "محله",
    "متراژ",
    "سال ساخت",
    "تعداد اتاق",
    "قیمت کل",
    "قیمت هر متر",
    "طبقه",
    "تاریخ انتشار",
    "لینک"
]


# ذخیره شخصی‌ها
with open(
    "divar_personal_clean.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(personal_results)


# ذخیره مشکوک‌ها
with open(
    "suspected_agency.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=suspected_fields
    )

    writer.writeheader()
    writer.writerows(suspected_results)


print("done")
print("شخصی:", len(personal_results))
print("مشکوک به املاکی:", len(suspected_results))
print(
    "مجموع:",
    len(personal_results) + len(suspected_results)
)