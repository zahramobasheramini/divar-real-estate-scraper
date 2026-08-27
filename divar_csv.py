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
results = []


for i, token in enumerate(tokens, start=1):
    url = f"https://api.divar.ir/v8/posts-v2/web/{token}"

    response = requests.get(url)

    if response.status_code != 200:
        continue

    ad_data = response.json()

    # فقط آگهی شخصی
    if ad_data.get("webengage", {}).get("business_type") != "personal":
        continue

    # فقط لاهیجان
    if ad_data.get("seo", {}).get("web_info", {}).get("city_persian") != "لاهیجان":
        continue

    result = {
        "نوع معامله": get_transaction_type(ad_data),
        "محله": ad_data.get("seo", {}).get("web_info", {}).get("district_persian"),
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

    results.append(result)

    print(f"{i} از {len(tokens)} گرفته شد: {token}")

    time.sleep(0.3)


# ذخیره CSV
fields = [
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

with open("divar_lahijan.csv", "w", newline="", encoding="utf-8-sig") as file:

    writer = csv.DictWriter(file, fieldnames=fields)

    writer.writeheader()
    writer.writerows(results)


print("done")
print("تعداد ذخیره شده:", len(results))