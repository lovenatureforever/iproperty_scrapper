import os
import gzip
import math
import requests
import json
import urllib3
import time
import pymysql
import string
import uuid
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common import NoSuchElementException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException

from appconfig_server import AppConfig
from logger import main_logger


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("disable-infobars")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    if AppConfig.USE_HEADLESS:
        options.add_argument("--headless=new")
    else:
        options.add_argument("--start-maximized")

    try:
        # driver = webdriver.Chrome(options=options, service=ChromeService(ChromeDriverManager().install()))
        # driver = webdriver.Chrome(options=options, service=ChromeService(executable_path='/home/smartappsystem/taas-insert/chromedriver'))
        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd("Page.enable", {})
        driver.execute_cdp_cmd("Runtime.enable", {})
        driver.execute_cdp_cmd("Network.enable", {})
        return driver
    except Exception as e:
        LOG.info(f"====================== Driver setup failed =======================\n Details: {e}", exc_info=True)
        return False

def __click_element__(driver, element, use_java=False):
    if use_java:
        driver.execute_script("arguments[0].click();", element)
    else:
        try:
            driver.execute_script("arguments[0].scrollIntoView();", element)
            element.click()
        except:
            ActionChains(driver).move_to_element(element).click().perform()


def wait_for_search_results(driver, timeout=5):
    """Wait for search results to load completely."""
    wait = WebDriverWait(driver, timeout)
    
    # Wait for listing list to be present
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul[data-test-id='listing-list']"))
    )
    
    # Wait for pagination to be present (indicates results are loaded)
    try:
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='pagination-wrapper'], .pagination-summary"))
        )
    except TimeoutException:
        # Pagination might not be present if few results
        pass
    
    # Additional wait for page to be fully loaded
    wait.until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def _pick_phone_by_label(phones_list, label_target):
    """Pick phone number by label (mobile, phone, whatsapp)."""
    for phone in phones_list:
        label = (phone.get("label") or "").lower()
        number = phone.get("number")
        if number and ("object" not in number) and (label_target in label):
            return number
    return None

def _prepare_item_data(item):
    # Basic info
    property_id = item.get("id", "")
    channel = item.get("channel", "")
    location_title = item.get("locationTitle", "")
    title = item.get("title", "")
    active = 1 if item.get("active", False) else 0
    
    # Price info
    price_info = item.get("prices", [])
    price_min = 0
    price_max = 0
    if price_info:
        price_min = price_info[0].get("min", 0)
        price_max = price_info[0].get("max", 0)
    
    # Address info
    address_obj = item.get("address", {})
    formatted_address = address_obj.get("formattedAddress", "")
    
    # organisations and listers
    organisations = item.get("organisations", [])
    organisation_type = ''
    organisation_name = ''
    organisation_phone = ''
    organisation_mobile = ''
    organisation_whatsapp = ''
    organisation_email = ''
    if organisations:
        organisation_type = organisations[0].get("type", '')
        organisation_name = organisations[0].get("name", '')
        organisation_contact = organisations[0].get("contact", {})
        organisation_phones = organisation_contact.get("phones", [])
        organisation_mobile = _pick_phone_by_label(organisation_phones, "mobile")
        organisation_whatsapp = _pick_phone_by_label(organisation_phones, "whatsapp")
        organisation_phone = _pick_phone_by_label(organisation_phones, "phone")
        organisation_email = organisation_contact.get("emails", [""])[0]

    listers = item.get("listers", [])
    lister_type = ''
    lister_name = ''
    lister_license = ''
    lister_phone = ''
    lister_mobile = ''
    lister_whatsapp = ''
    lister_email = ''
    if listers:
        lister_type = listers[0].get("type", "")
        lister_name = listers[0].get("name", "")
        lister_license = listers[0].get("license", "")
        lister_contact = listers[0].get("contact", {})
        lister_phones = lister_contact.get("phones", [])
        lister_mobile = _pick_phone_by_label(lister_phones, "mobile")
        lister_whatsapp = _pick_phone_by_label(lister_phones, "whatsapp")
        lister_phone = _pick_phone_by_label(lister_phones, "phone")
        lister_email = lister_contact.get("emails", [""])[0]
    
    return {
        "channel": channel,
        "property_id": property_id,
        "title": title,
        "location_title": location_title,
        "active": active,
        "address": formatted_address,
        "price_min": price_min,
        "price_max": price_max,
        "organisation_type": organisation_type,
        "organisation_name": organisation_name,
        "organisation_phone": organisation_phone,
        "organisation_mobile": organisation_mobile,
        "organisation_whatsapp": organisation_whatsapp,
        "organisation_email": organisation_email,
        "lister_type": lister_type,
        "lister_name": lister_name,
        "lister_license": lister_license,
        "lister_phone": lister_phone,
        "lister_mobile": lister_mobile,
        "lister_whatsapp": lister_whatsapp,
        "lister_email": lister_email
    }

def handle_api_response(json_data, keyword='', tab='buy', state='All States'):
    conn = None
    try:
        # Extract response metadata
        total_count = json_data.get("totalCount", 0)
        next_page_token = json_data.get("nextPageToken", "")
        LOG.info(f"API Response - Total Count: {total_count}, Next Page: {next_page_token}")
        
        # Get items to process
        items = json_data.get("items", [])
        LOG.info(f"Found {len(items)} listings in API response")
        
        if not items:
            LOG.info("No items to process")
            return
        
        # Database connection
        conn = pymysql.connect(
            host=AppConfig.MYSQL_SERVER,
            user=AppConfig.MYSQL_USER,
            passwd=AppConfig.MYSQL_PASSWORD,
            db=AppConfig.MYSQL_DATABASE,
            connect_timeout=20,
            read_timeout=60
        )

        # SQL for upsert
        insert_sql = """
            INSERT INTO items (
                channel, property_id, title, location_title, active, address, price_min, price_max,
                organisation_type, organisation_name, organisation_phone, organisation_mobile, organisation_whatsapp, organisation_email,
                lister_type, lister_name, lister_license,
                lister_phone, lister_mobile, lister_whatsapp, lister_email, keyword, tab, state
            ) VALUES (
                %(channel)s, %(property_id)s, %(title)s, %(location_title)s, %(active)s, %(address)s, %(price_min)s, %(price_max)s,
                %(organisation_type)s, %(organisation_name)s, %(organisation_phone)s, %(organisation_mobile)s, %(organisation_whatsapp)s, %(organisation_email)s,
                %(lister_type)s, %(lister_name)s, %(lister_license)s,
                %(lister_phone)s, %(lister_mobile)s, %(lister_whatsapp)s, %(lister_email)s, %(keyword)s, %(tab)s, %(state)s
            )
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                location_title = VALUES(location_title),
                active = VALUES(active),
                address = VALUES(address),
                price_min = VALUES(price_min),
                price_max = VALUES(price_max),
                organisation_type = VALUES(organisation_type),
                organisation_name = VALUES(organisation_name),
                organisation_phone = VALUES(organisation_phone),
                organisation_mobile = VALUES(organisation_mobile),
                organisation_whatsapp = VALUES(organisation_whatsapp),
                organisation_email = VALUES(organisation_email),
                lister_type = VALUES(lister_type),
                lister_name = VALUES(lister_name),
                lister_license = VALUES(lister_license),
                lister_phone = VALUES(lister_phone),
                lister_mobile = VALUES(lister_mobile),
                lister_whatsapp = VALUES(lister_whatsapp),
                lister_email = VALUES(lister_email),
                keyword = VALUES(keyword),
                tab = VALUES(tab),
                state = VALUES(state)
        """
        
        # Process each item
        with conn.cursor() as cursor:
            processed_count = 0
            error_count = 0
            
            for i, item in enumerate(items, 1):
                try:
                    # Prepare data for insertion
                    item_data = _prepare_item_data(item)
                    item_data["keyword"] = keyword
                    item_data["tab"] = tab
                    item_data["state"] = state
                    # Insert/update record
                    cursor.execute(insert_sql, item_data)
                    processed_count += 1
                
                except Exception as e:
                    error_count += 1
                    LOG.error(f"Error processing listing {i}: {e}", exc_info=True)
                    continue
        
            # Commit all changes
            conn.commit()
            LOG.info(f"Successfully processed {processed_count} listings, {error_count} errors")
        
    except Exception as e:
        if conn:
            conn.rollback()
        LOG.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()

def clear_performance_logs(driver):
    """Clear performance logs to prevent accumulation."""
    try:
        driver.get_log("performance")
    except Exception as e:
        LOG.debug(f"Error clearing performance logs: {e}")

def find_request_ids(driver, url_pattern):
    ids = []
    try:
        for entry in driver.get_log("performance"):
            try:
                msg = json.loads(entry["message"])["message"]
                if msg.get("method") == "Network.responseReceived":
                    p = msg.get("params", {})
                    url = p.get("response", {}).get("url", "")
                    if re.search(url_pattern, url):
                        request_id = p.get("requestId")
                        if request_id:
                            ids.append(request_id)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                LOG.debug(f"Error parsing performance log entry: {e}")
                continue
    except Exception as e:
        LOG.error(f"Error getting performance logs: {e}")
    return ids

def find_next_page_button(driver, timeout=10):
    try:
        wait = WebDriverWait(driver, timeout)
        
        # Check for next page button (not disabled)
        next_page_selectors = [
            "//li[@class='pagination-item']//a[@aria-label='Go to next page']",
            "//a[@aria-label='Go to next page']",
            ".pagination-item a[aria-label='Go to next page']"
        ]
        
        for selector in next_page_selectors:
            try:
                if selector.startswith("//"):
                    element = driver.find_element(By.XPATH, selector)
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                
                # Check if element is clickable and not disabled
                if element.is_enabled() and element.is_displayed():
                    return element
            except:
                continue
        
        return None
        
    except Exception as e:
        LOG.debug(f"Error checking for next page: {e}")
        return None

def click_next_page_button(driver, timeout=10):
    try:
        wait = WebDriverWait(driver, timeout)
        next_page_button = find_next_page_button(driver, timeout=2)
        if next_page_button:
            time.sleep(1)
            __click_element__(driver, next_page_button, use_java=True)
            return True
        else:
            LOG.warning("Next page button not found")
            return False
            
    except Exception as e:
        LOG.error(f"Error clicking next page: {e}")
        return False

def main(keyword='ativo suites', tab='buy', state='All States'):
    try:
        driver = setup_driver()
        if not driver:
            return
        driver.get("https://www.iproperty.com.my/")
        wait = WebDriverWait(driver, 60)
        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # Input keyword into Ant Design search field
        search_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-select-search__field"))
        )
        search_input.clear()
        time.sleep(1)
        
        search_input.send_keys("ativo suites")
        time.sleep(2)
        search_input.send_keys(Keys.ENTER)
        time.sleep(3)
        
        # Clear any existing performance logs
        clear_performance_logs(driver)
        time.sleep(2)  # Wait for logs to clear
        
        next_page = 2
        while next_page:
            # Wait for search result
            for _ in range(4):
                try:
                    wait_for_search_results(driver)
                    break
                except Exception:
                    driver.refresh()
                    time.sleep(10)
                    continue
            
            time.sleep(10)

            # Process first page
            ids = find_request_ids(driver, r"/consumer/api/listing-search-with-auth")
            data_found = False
            
            for rid in ids:
                try:
                    body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": rid})
                    if body and body.get("body"):
                        data = json.loads(body["body"])
                        next_page = data.get("nextPageToken", 0)
                        handle_api_response(data, keyword, tab, state)
                        data_found = True
                        break
                except Exception as e:
                    LOG.warning(f"Error getting response body for request {rid}: {e}")
                    continue

            if not data_found:
                LOG.warning("No API response data found, skipping this page")
                next_page = 0

            if next_page:
                click_next_page_button(driver)
    except Exception as e:
        LOG.info(f"Error: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    LOG = main_logger("iProperty")
    main()
