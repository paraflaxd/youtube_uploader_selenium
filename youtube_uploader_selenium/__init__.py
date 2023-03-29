"""This module implements uploading videos on YouTube via Selenium using metadata JSON file
    to extract its title, description etc."""

from typing import DefaultDict, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import json
from .Constant import *
from pathlib import Path
import logging
import time
from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import platform
import random
import sys

logging.basicConfig()

def load_metadata(metadata_json_path: Optional[str] = None) -> DefaultDict[str, str]:
	if metadata_json_path is None:
		return defaultdict(str)
	with open(metadata_json_path, encoding='utf-8') as metadata_json_file:
		return defaultdict(str, json.load(metadata_json_file))


class YouTubeUploader:
	"""A class for uploading videos on YouTube via Selenium using metadata JSON file
	to extract its title, description etc"""

	def __init__(self, video_path: str, metadata_json_path: Optional[str] = None,
	             thumbnail_path: Optional[str] = None,
	             profile_path: Optional[Path] = Path('profile')) -> None:
		self.video_path = video_path
		self.thumbnail_path = thumbnail_path
		self.metadata_dict = load_metadata(metadata_json_path)
		
		options = ChromeOptions()
		if(profile_path):
			absolute_path = str(profile_path.absolute())
			options.add_argument('--user-data-dir='+absolute_path)
		options.add_argument("--disable-blink-features=AutomationControlled")
		options.add_argument("--disable-infobars")
		options.add_argument("--mute-audio")
		self.browser = Chrome(options=options)
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.DEBUG)
		self.__validate_inputs()

		self.is_mac = False
		if not any(os_name in platform.platform() for os_name in ["Windows", "Linux"]):
			self.is_mac = True

	def __validate_inputs(self):
		if not self.metadata_dict[Constant.VIDEO_TITLE]:
			self.logger.warning(
				"The video title was not found in a metadata file")
			self.metadata_dict[Constant.VIDEO_TITLE] = Path(
				self.video_path).stem
			self.logger.warning("The video title was set to {}".format(
				Path(self.video_path).stem))
		if not self.metadata_dict[Constant.VIDEO_DESCRIPTION]:
			self.logger.warning(
				"The video description was not found in a metadata file")

	def upload(self) -> bool:
		try:
			self.__login()
			self.__upload()
			self.__quit()
			return True
		except Exception as e:
			print(e)
			return False

	def __login(self):
		time.sleep(1.321)

		self.browser.get('https://youtube.com/')

		def isLoggedIn() -> bool:
			has_cookie = self.browser.get_cookie(Constant.YOUTUBE_LOGIN_COOKIE)
			on_home_page = self.browser.current_url.endswith('.com/')
			if(has_cookie and on_home_page):
				return True
			return False

		if(isLoggedIn()):
			return

		while(not isLoggedIn()):
			sleep_time = random.uniform(5, 8)
			print('sleeping: ' + str(sleep_time))
			time.sleep(sleep_time)

	def __clear_field(self, field):
		self.__click(field)
		time.sleep(Constant.USER_WAITING_TIME)
		if self.is_mac:
			field.send_keys(Keys.COMMAND + 'a')
		else:
			field.send_keys(Keys.CONTROL + 'a')
		time.sleep(Constant.USER_WAITING_TIME)
		field.send_keys(Keys.BACKSPACE)

	def __write_in_field(self, field, string, select_all=False):
		if select_all:
			self.__clear_field(field)
		else:
			self.__click(field)
			time.sleep(Constant.USER_WAITING_TIME)

		field.send_keys(string)

	def __click(self, element):
		actions = ActionChains(self.browser)
		actions.move_to_element(element).click().perform()

	def __upload(self) -> Tuple[bool, Optional[str]]:

		edit_mode = self.metadata_dict[Constant.VIDEO_EDIT]
		if edit_mode:
			self.browser.get(edit_mode)
			time.sleep(Constant.USER_WAITING_TIME)
		else:
			self.browser.get(Constant.YOUTUBE_URL)
			time.sleep(Constant.USER_WAITING_TIME)
			self.browser.get(Constant.YOUTUBE_UPLOAD_URL)
			time.sleep(Constant.USER_WAITING_TIME)
			absolute_video_path = str(Path.cwd() / self.video_path)
			self.browser.find_element(By.XPATH, Constant.INPUT_FILE_VIDEO).send_keys(
				absolute_video_path)
			self.logger.debug('Attached video {}'.format(self.video_path))

			# Find status container
			WebDriverWait(self.browser, sys.maxsize).until(
				EC.presence_of_element_located((By.XPATH, Constant.UPLOADING_STATUS_CONTAINER))
			)

		if self.thumbnail_path is not None:
			absolute_thumbnail_path = str(Path.cwd() / self.thumbnail_path)
			self.browser.find_element(By.XPATH, Constant.INPUT_FILE_THUMBNAIL).send_keys(
				absolute_thumbnail_path)
			change_display = "document.getElementById('file-loader').style = 'display: block! important'"
			self.browser.execute_script(change_display)
			self.logger.debug(
				'Attached thumbnail {}'.format(self.thumbnail_path))
		
		try:
			WebDriverWait(self.browser, 5).until(
				EC.presence_of_element_located((By.XPATH, Constant.REUSE_DETAILS_BUTTON))
			).click()
		except:
			pass

		fields = WebDriverWait(self.browser, 10).until(
			EC.presence_of_all_elements_located((By.ID, Constant.TEXTBOX_ID))
		)
		title_field, description_field = fields

		self.__write_in_field(
			title_field, self.metadata_dict[Constant.VIDEO_TITLE], select_all=True)
		self.logger.debug('The video title was set to \"{}\"'.format(
			self.metadata_dict[Constant.VIDEO_TITLE]))

		video_description = self.metadata_dict[Constant.VIDEO_DESCRIPTION]
		video_description = video_description.replace("\n", Keys.ENTER)
		if video_description:
			self.__write_in_field(description_field, video_description, select_all=True)
			self.logger.debug('Description filled.')

		kids_section = self.browser.find_element(By.NAME, Constant.NOT_MADE_FOR_KIDS_LABEL)
		self.browser.execute_script("arguments[0].scrollIntoView();", kids_section)
		time.sleep(Constant.USER_WAITING_TIME)
		radio_labels = self.browser.find_elements(By.ID, Constant.RADIO_LABEL)
		radio_labels[1].click()

		# Playlist
		playlist = self.metadata_dict[Constant.VIDEO_PLAYLIST]
		if playlist:
			self.browser.find_element(By.CLASS_NAME, Constant.PL_DROPDOWN_CLASS).click()
			time.sleep(Constant.USER_WAITING_TIME)
			search_field = self.browser.find_element(By.ID, Constant.PL_SEARCH_INPUT_ID)
			self.__write_in_field(search_field, playlist)
			time.sleep(Constant.USER_WAITING_TIME * 2)
			playlist_items_container = self.browser.find_element(By.ID, Constant.PL_ITEMS_CONTAINER_ID)
			# Try to find playlist
			self.logger.debug('Playlist xpath: "{}".'.format(Constant.PL_ITEM_CONTAINER.format(playlist)))
			playlist_item = playlist_items_container.find_element(By.XPATH, Constant.PL_ITEM_CONTAINER.format(playlist))
			if playlist_item:
				self.logger.debug('Playlist found.')
				playlist_item.click()
				time.sleep(Constant.USER_WAITING_TIME)
			else:
				self.logger.debug('Playlist not found. Creating')
				self.__clear_field(search_field)
				time.sleep(Constant.USER_WAITING_TIME)

				new_playlist_button = self.browser.find_element(By.CLASS_NAME, Constant.PL_NEW_BUTTON_CLASS)
				new_playlist_button.click()

				create_playlist_container = self.browser.find_element(By.ID, Constant.PL_CREATE_PLAYLIST_CONTAINER_ID)
				playlist_title_textbox = create_playlist_container.find_element(By.XPATH, "//textarea")
				self.__write_in_field(playlist_title_textbox, playlist)

				time.sleep(Constant.USER_WAITING_TIME)
				create_playlist_button = self.browser.find_element(By.CLASS_NAME, Constant.PL_CREATE_BUTTON_CLASS)
				create_playlist_button.click()
				time.sleep(Constant.USER_WAITING_TIME)

			done_button = self.browser.find_element(By.CLASS_NAME, Constant.PL_DONE_BUTTON_CLASS)
			done_button.click()

		# Advanced options
		self.browser.find_element(By.ID, Constant.ADVANCED_BUTTON_ID).click()
		self.logger.debug('Clicked MORE OPTIONS')
		time.sleep(Constant.USER_WAITING_TIME)

		# Tags
		tags = self.metadata_dict[Constant.VIDEO_TAGS]
		if tags:
			tags_container = self.browser.find_element(By.ID, Constant.TAGS_CONTAINER_ID)
			tags_field = tags_container.find_element(By.ID, Constant.TAGS_INPUT)
			self.__write_in_field(tags_field, ','.join(tags))
			self.logger.debug('The tags were set to \"{}\"'.format(tags))


		self.browser.find_element(By.ID, Constant.NEXT_BUTTON).click()
		self.logger.debug('Clicked {} one'.format(Constant.NEXT_BUTTON))

		self.browser.find_element(By.ID, Constant.NEXT_BUTTON).click()
		self.logger.debug('Clicked {} two'.format(Constant.NEXT_BUTTON))

		self.browser.find_element(By.ID, Constant.NEXT_BUTTON).click()
		self.logger.debug('Clicked {} three'.format(Constant.NEXT_BUTTON))

		schedule = self.metadata_dict[Constant.VIDEO_SCHEDULE]
		if schedule:
			upload_time_object = datetime.strptime(schedule, "%m/%d/%Y, %H:%M")
			self.browser.find_element(By.ID, Constant.SCHEDULE_CONTAINER_ID).click()
			self.browser.find_element(By.ID, Constant.SCHEDULE_DATE_ID).click()
			self.browser.find_element(By.XPATH, Constant.SCHEDULE_DATE_TEXTBOX).clear()
			self.browser.find_element(By.XPATH, Constant.SCHEDULE_DATE_TEXTBOX).send_keys(
				datetime.strftime(upload_time_object, "%b %e, %Y"))
			self.browser.find_element(By.XPATH, Constant.SCHEDULE_DATE_TEXTBOX).send_keys(Keys.ENTER)
			self.browser.find_element(By.XPATH, Constant.SCHEDULE_TIME).click()
			self.browser.find_element(By.XPATH, Constant.SCHEDULE_TIME).clear()
			self.browser.find_element(By.XPATH, Constant.SCHEDULE_TIME).send_keys(
				datetime.strftime(upload_time_object, "%H:%M"))
			self.browser.find_element(By.XPATH, Constant.SCHEDULE_TIME).send_keys(Keys.ENTER)
			self.logger.debug(f"Scheduled the video for {schedule}")
		else:
			public_main_button = self.browser.find_element(By.NAME, Constant.PUBLIC_BUTTON)
			public_main_button.find_element(By.ID, Constant.RADIO_LABEL).click()
			self.logger.debug('Made the video {}'.format(Constant.PUBLIC_BUTTON))

		video_id = self.__get_video_id()
		done_button = self.browser.find_element(By.ID, Constant.DONE_BUTTON)

		# Catch such error as
		# "File is a duplicate of a video you have already uploaded"
		if done_button.get_attribute('aria-disabled') == 'true':
			error_message = self.browser.find_element(By.XPATH, Constant.ERROR_CONTAINER).text
			self.logger.error(error_message)
			return False, None

		done_button.click()
		self.logger.debug(
			"Published the video with video_id = {}".format(video_id))
		time.sleep(Constant.USER_WAITING_TIME)
		self.browser.get(Constant.YOUTUBE_URL)
		self.__quit()
		return True, video_id

	def __get_video_id(self) -> Optional[str]:
		video_id = None
		try:
			video_url_container = self.browser.find_element(
				By.XPATH, Constant.VIDEO_URL_CONTAINER)
			video_url_element = video_url_container.find_element(By.XPATH, Constant.VIDEO_URL_ELEMENT)
			video_id = video_url_element.get_attribute(
				Constant.HREF).split('/')[-1]
		except:
			self.logger.warning(Constant.VIDEO_NOT_FOUND_ERROR)
			pass
		return video_id

	def __quit(self):
		self.browser.quit()