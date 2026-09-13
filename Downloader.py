import os
import re
import time


from datetime import date, datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

service = Service(executable_path="")
driver = webdriver.Chrome(service=service)

action_button = driver.find_element(By.CLASS_NAME,"btn-primary")
action_button.click()