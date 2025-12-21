import asyncio
import json
from collections.abc import Callable
from traceback import format_exc
from typing import TYPE_CHECKING

import questionary
from loguru import logger

from apis import CourseAPI
from models import (
    ChapterInfoAPIResponse,
    ConfigModel,
    CourseAPIUserInfoAPIResponse,
    CourseListAPIResponse,
    CoursewareChapter,
    CoursewarePage,
    ElementQuestion,
    ElementVideo,
    ModelCourse,
    ModelTextbook,
    QuestionAnswerAPIResponse,
    StudyRecordAPIResponse,
    TextbookInfoAPIResponse,
    TextbookListAPIResponse,
)
from .data_manager import DataManager
from utils import answer, sync_text_decrypt

if TYPE_CHECKING:
    from config import Config
    from services import HttpClient


class CoursewareManager:
    """课件管理类"""

    def __init__(self, username: str, config: "Config", client: "HttpClient") -> None:
        """
        课件管理类初始化

        :param username: 活跃用户名
        :type username: str
        :param config: 配置对象
        :type config: "Config"
        :param client: 内部Http客户端对象
        :type client: "HttpClient"
        """

        self.user_config = config.users[username]
        self.config = config
        self.client = client
        self.course_api = CourseAPI(username=username, config=config, client=client)
        self.data_manager = DataManager()

    async def menu(self) -> None:
        """课件管理菜单"""
        logger.debug("[MANAGER][COURSEWARE] 课件管理菜单")

        # 初始化选项
        choices: list[str] = [
            "课件配置",
            "开始刷课",
            "查看刷课信息",
            "删除课件",
            "修改刷课上报时长",
            "清理已刷完课程",
            "返回",
        ]
        choices_map: dict[str, Callable] = {
            "课件配置": self.__courseware_config,
            "开始刷课": self.__start_courseware,
            "查看刷课信息": self.__print_courseware_info,
            "删除课件": self.__remove_courseware,
            "修改刷课上报时长": self.__modify_study_time,
            "清理已刷完课程": self.__prune_completed_courseware,
            "解密同步学习记录请求数据": self.__decrypt_sync_study_record_request,
            "返回": lambda: None,
        }

        if self.config.debug:
            choices.append("解密同步学习记录请求数据")

        try:
            while True:
                choice = await answer(
                    questionary.select(
                        message="[课程管理菜单] 请选择",
                        choices=choices,
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )

                if choice == "返回":
                    return None

                await choices_map[choice]()

        except KeyboardInterrupt as e:
            logger.info("[MANAGER][COURSEWARE] 用户强制退出课程管理")
            return None

        except Exception as e:
            logger.error(
                f"{format_exc()}\n[MANAGER][COURSEWARE] 课程管理菜单出现异常: {e}"
            )
            return None

    async def __courseware_config(self) -> None:
        """课件配置"""
        logger.debug("[MANAGER][COURSEWARE] 课件配置")

        try:
            # 获取用户的课程列表
            courses = await self.course_api.get_courses()
            if not courses:
                return None

            # 生成课程选项 list["[课程ID] 课程名称"]
            course_choices = [
                f"[{course.id}] {course.name}" for course in courses.courseList
            ]

            # 获取用户选择的课程
            raw_selected_course_ids: list[str] = await answer(
                questionary.checkbox(
                    message="请选择要刷的课程",
                    choices=course_choices,
                    validate=lambda x: len(x) > 0 or "不可为空, 请选择",
                    instruction="(使用方向键移动，空格键选择，a键全选/取消，i键反选)",
                )
            )

            selected_course_ids: list[int]

            # 解析选择的课程为课程ID列表
            selected_course_ids = [
                int(course_id.split("]")[0].split("[")[1].strip())
                for course_id in raw_selected_course_ids
            ]

            # 转换课程ID列表为课程信息对象字典
            selected_course_infos: dict[int, CourseListAPIResponse._Course] = {
                course.id: course
                for course in courses.courseList
                if course.id in selected_course_ids
            }

            # 初始化已选择的课程的所有教材列表{课程ID: {教材ID: 教材信息}}
            selected_course_textbook_infos: dict[
                int, dict[int, TextbookListAPIResponse.TextbookInfo]
            ] = {}

            # 解析每个课程的教材
            for (
                selected_course_id,
                selected_course_info,
            ) in selected_course_infos.items():

                # 获取教材
                textbooks = await self.course_api.get_textbooks(
                    course_id=selected_course_id
                )

                if not textbooks:
                    logger.warning(f"课程 {selected_course_info.name} 获取教材失败")
                    continue

                # 初始化已选择的课程的教材列表
                selected_course_textbook_infos[selected_course_id] = {}
                selected_course_textbooks = selected_course_textbook_infos[
                    selected_course_id
                ]
                # 添加教材信息
                for textbook in textbooks.textbooks:
                    selected_course_textbooks[textbook.courseId] = textbook

            # 生成教材选项
            textbook_choices = [
                f"'{selected_course_infos[course_id].name}' [{textbook_id}] {textbook_info.name}"
                for course_id, selected_course_textbook_info in selected_course_textbook_infos.items()
                for textbook_id, textbook_info in selected_course_textbook_info.items()
            ]

            if not textbook_choices:
                logger.warning("没有可配置的教材")
                return None

            # 获取用户选择的教材
            raw_selected_textbook_ids: list[str] = await answer(
                questionary.checkbox(
                    message="请选择要刷的教材",
                    choices=textbook_choices,
                    validate=lambda x: len(x) > 0 or "不可为空, 请选择",
                    instruction="(使用方向键移动，空格键选择，a键全选/取消，i键反选)",
                )
            )

            # 解析选择的教材为ID列表
            selected_textbook_ids: list[int] = [
                int(textbook_id.split("'")[2].split("[")[1].split("]")[0].strip())
                for textbook_id in raw_selected_textbook_ids
            ]

            # 转换教材ID列表为教材信息对象字典
            selected_textbook_infos: dict[int, TextbookListAPIResponse.TextbookInfo] = {
                textbook_id: textbook_info
                for course_id, selected_course_textbook_info in selected_course_textbook_infos.items()
                for textbook_id, textbook_info in selected_course_textbook_info.items()
                if textbook_id in selected_textbook_ids
            }

            # 初始化课件配置对象从已选中的课程中
            course_config: dict[int, ModelCourse] = {
                course_id: ModelCourse(
                    course_id=course_id,
                    course_name=course_info.name,
                    class_id=course_info.classId,
                    class_user_id=course_info.classUserId,
                    textbooks={
                        selected_textbook_id: ModelTextbook(
                            textbook_id=selected_textbook_id,
                            textbook_name=selected_textbook_info.name,
                            status=selected_textbook_info.status,
                            limit=selected_textbook_info.limit,
                        )
                        for selected_textbook_id, selected_textbook_info in selected_textbook_infos.items()
                        if selected_textbook_id
                        in selected_course_textbook_infos[course_id].keys()
                    },
                )
                for course_id, course_info in selected_course_infos.items()
            }

            await self.__complete_courseware(course_config)

            self.user_config.courses = course_config
            self.config.save()

            await self.__print_courseware_info()

            logger.success("课件配置成功, 请使用 '开始刷课' 启动刷课")

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][COURSEWARE] 课件配置出错: {e}")
            return None

    async def __complete_courseware(
        self, course_config: dict[int, ModelCourse]
    ) -> None:
        """获取教材详细信息, 章节信息, 节信息, 答案信息, 视频信息补全课程配置对象"""
        logger.debug("[MANAGER][COURSEWARE] 补全课件信息")

        # 遍历课程
        for course_id, course_info in course_config.items():
            # 创建引用
            textbooks = course_info.textbooks
            course_name = course_info.course_name

            logger.info(f"[课程][{course_name}] 开始解析")

            # 收集获取教材信息的协程对象列表
            coros_get_textbook_info = []
            for textbook_id, textbook_info in textbooks.items():
                coros_get_textbook_info.append(
                    self.course_api.get_textbook_info(
                        textbook_id=textbook_id, class_id=course_info.class_id
                    )
                )

            # 异步调度
            results_get_textbook_info = await asyncio.gather(*coros_get_textbook_info)

            # 解析异步调度信息
            parsed_textbook_infos: dict[int, TextbookInfoAPIResponse] = {}
            for result in results_get_textbook_info:
                for textbook_id, textbook_info in result.items():
                    parsed_textbook_infos[textbook_id] = textbook_info

            logger.success(
                f"[课程][{course_name}] 获取到 {len(parsed_textbook_infos)} 个教材信息"
            )

            # 遍历教材
            for textbook_id, textbook_info in textbooks.items():

                # 获取教材信息
                resp_textbook_info = parsed_textbook_infos[textbook_id]

                # 跳过获取失败的教材信息
                if not resp_textbook_info:
                    logger.warning(
                        f"尝试获取教材 '{textbook_info.textbook_name}' 详细信息失败, 跳过"
                    )
                    continue

                # 解析教材信息
                self.data_manager.parse_textbook_info(
                    course_config=course_config[course_id],
                    textbook_info=resp_textbook_info,
                )

                # 创建引用
                chapters = textbook_info.chapters
                textbook_name = textbook_info.textbook_name

                logger.info(f"[教材][{textbook_name}] 开始解析")

                # 收集获取章节信息的协程对象列表
                coros_get_textbook_info = []
                for chapter_id, chapter_info in chapters.items():
                    coros_get_textbook_info.append(
                        self.course_api.get_chapter_info(chapter_id=chapter_id)
                    )

                # 异步调度
                results_get_chapter_info = await asyncio.gather(
                    *coros_get_textbook_info
                )

                # 解析异步调度信息
                parsed_chapter_infos: dict[int, ChapterInfoAPIResponse] = {}
                for result in results_get_chapter_info:
                    for chapter_id, chapter_info in result.items():
                        parsed_chapter_infos[chapter_id] = chapter_info

                logger.success(
                    f"[教材][{textbook_name}] 获取到 {len(parsed_chapter_infos)} 个章节信息"
                )

                for chapter_id, chapter_info in chapters.items():
                    # 获取章节信息
                    resp_chapter_info = parsed_chapter_infos[chapter_id]

                    # 跳过获取失败的章节信息
                    if not resp_chapter_info:
                        logger.warning(
                            f"尝试获取章节 '{chapter_info.chapter_name}' 详细信息失败, 跳过"
                        )
                        continue

                    # 解析章节信息
                    self.data_manager.parse_chapter_info(
                        course_config=course_config[course_id],
                        textbook_id=textbook_id,
                        chapter_info=resp_chapter_info,
                    )

                    # 创建引用
                    sections = chapter_info.sections
                    chapter_name = chapter_info.chapter_name

                    logger.info(f"[章节][{chapter_name}] 开始解析")

                    # 收集获取学习记录信息的协程对象列表
                    coros_get_study_record_info = []
                    for section_id, section_info in sections.items():
                        coros_get_study_record_info.append(
                            self.course_api.get_study_record_info(section_id=section_id)
                        )

                    # 异步调度
                    results_get_study_record_info = await asyncio.gather(
                        *coros_get_study_record_info
                    )

                    # 解析异步调度信息
                    parsed_study_record_infos: dict[
                        int, tuple[bool, StudyRecordAPIResponse | None]
                    ] = {}
                    for result in results_get_study_record_info:
                        for section_id, (status, study_record_info) in result.items():
                            parsed_study_record_infos[section_id] = (
                                status,
                                study_record_info,
                            )

                    logger.success(
                        f"[章节][{chapter_name}] 获取到 {len(parsed_study_record_infos)} 个学习记录信息"
                    )

                    # 遍历节
                    for section_id, section_info in sections.items():
                        # 创建引用
                        pages: dict[int, CoursewarePage] = section_info.pages

                        # 遍历页面
                        for page_id, page_info in pages.items():
                            # 如果页面类型为题目
                            if page_info.page_content_type == 7:
                                elements = page_info.elements

                                # 遍历元素
                                for element_info in elements:
                                    if not isinstance(element_info, ElementQuestion):
                                        raise

                                    logger.info(
                                        f"[题目][{page_info.page_name}] 开始解析"
                                    )

                                    # 收集获取题目答案信息的协程对象列表
                                    coros_get_question_answer_list = []
                                    for question_info in element_info.questions:
                                        question_id = question_info.question_id
                                        coros_get_question_answer_list.append(
                                            self.course_api.get_question_answer_list(
                                                question_id=question_id,
                                                parent_id=page_id,
                                            )
                                        )

                                    # 异步调度
                                    results_get_question_answer_list = (
                                        await asyncio.gather(
                                            *coros_get_question_answer_list
                                        )
                                    )

                                    # 解析异步调度信息
                                    parsed_question_answer_lists: dict[
                                        int, QuestionAnswerAPIResponse
                                    ] = {}
                                    for result in results_get_question_answer_list:
                                        for (
                                            question_id,
                                            question_answer_list,
                                        ) in result.items():
                                            parsed_question_answer_lists[
                                                question_id
                                            ] = question_answer_list

                                    logger.success(
                                        f"[题目][{page_info.page_name}] 获取到 {len(parsed_question_answer_lists)} 个问题的答案列表"
                                    )

                                    # 遍历问题元素的所有问题
                                    for question_info in element_info.questions:
                                        question_id = question_info.question_id

                                        # 获取问题答案列表
                                        resp_question_answer_list = (
                                            parsed_question_answer_lists[question_id]
                                        )

                                        # 答案获取失败
                                        if not resp_question_answer_list:
                                            logger.warning(
                                                f"尝试获取问题 ID-{question_id} 答案列表失败"
                                            )
                                            raise

                                        # 补全答案列表
                                        question_info.question_answer_list = (
                                            resp_question_answer_list.correctAnswerList
                                        )

                        # 创建引用
                        section_name = section_info.section_name
                        resp_status, resp_study_record_info = parsed_study_record_infos[
                            section_id
                        ]

                        # 跳过获取失败的学习记录
                        if not resp_status:
                            logger.warning(
                                f"尝试获取学习记录 '{section_name}' 失败, 跳过"
                            )
                            continue

                        # 未学习 跳过
                        if not resp_study_record_info:
                            continue

                        # 解析学习记录信息
                        self.data_manager.parse_study_record_info(
                            course_config=course_config[course_id],
                            textbook_id=textbook_id,
                            study_record_info=resp_study_record_info,
                        )

        # 清理空的课件
        for course_id, course_info in dict(course_config).items():
            course_info.prune()
            if not course_info.textbooks:
                course_config.pop(course_id)

    async def __start_courseware_confirm(self) -> bool:
        logger.debug("[MANAGER][COURSEWARE] 开始刷课前确认")

        try:
            await self.__print_courseware_info()
            logger.warning("请再次查看此次刷课信息")
            logger.warning(
                "确认课件信息是否正确, 确认页面类型是否正确 (视频/题目/文档/纯文本)"
            )

            while True:
                choices = [
                    "默认模式 (开始前清理已刷完课程)",
                    "全刷模式 (不清理已刷完课程)",
                    "再次查看此次刷课信息",
                    "返回",
                ]
                choice = await answer(
                    questionary.select(
                        message="请在开始刷课前进行确认",
                        choices=choices,
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )
                if choice == choices[0]:
                    await self.__prune_completed_courseware()
                    return True

                elif choice == choices[1]:
                    return True

                elif choice == choices[2]:
                    await self.__print_courseware_info()
                    continue

                elif choice == choices[3]:
                    break

            return False

        except Exception as e:
            return False

    async def __start_courseware(self) -> None:
        """开始刷课"""
        logger.debug("[MANAGER][COURSEWARE] 开始刷课")

        try:

            async def courseware_handler(
                chapters: dict[int, CoursewareChapter],
                user_info: CourseAPIUserInfoAPIResponse,
                is_first: bool,
            ) -> None:
                """
                内部处理课件函数

                :param chapters: 章节信息字典
                :type chapters: dict[int, CoursewareChapter]
                :param user_info: 用户信息对象
                :type user_info: CourseAPIUserInfoAPIResponse
                :param is_first: 是否为第一次处理课件
                :type is_first: bool
                """

                # 遍历章
                for chapter_id, chapter_info in chapters.items():
                    # 创建引用
                    chapter_name = chapter_info.chapter_name
                    sections = chapter_info.sections

                    logger.info(f"[章][{chapter_id}] 开始处理 '{chapter_name}'")

                    # 遍历节
                    for section_id, section_info in sections.items():
                        # 初始化课件-节, 获取开始学习的时间戳
                        study_start_time = await self.course_api.initialize_section(
                            section_id=section_id
                        )

                        # 初始化失败
                        if not study_start_time:
                            logger.warning(
                                f"初始化节 '{section_info.section_name}' 失败, 跳过"
                            )
                            continue

                        if not is_first:
                            # 创建引用
                            pages = section_info.pages

                            # 遍历页面
                            for page_id, page_info in pages.items():
                                # 如果页面类型为视频
                                if page_info.page_content_type == 6:

                                    # 收集上报视频观看行为的协程对象列表
                                    coros_watch_video_behavior = []
                                    for element_info in page_info.elements:
                                        # 跳过非视频元素
                                        if not isinstance(element_info, ElementVideo):
                                            continue
                                        # 创建引用
                                        video_id = element_info.video_id
                                        coros_watch_video_behavior.append(
                                            self.course_api.watch_video_behavior(
                                                class_id=class_id,
                                                textbook_id=textbook_id,
                                                chapter_id=chapter_id,
                                                video_id=video_id,
                                            )
                                        )

                                    # 异步调度
                                    results_watch_video_behavior = await asyncio.gather(
                                        *coros_watch_video_behavior
                                    )

                                    # 解析异步调度信息
                                    parsed_watch_video_behaviors: dict[int, bool] = {}
                                    for result in results_watch_video_behavior:
                                        for video_id, watch_status in result.items():
                                            parsed_watch_video_behaviors[video_id] = (
                                                watch_status
                                            )

                                    # 遍历所有元素
                                    for element_info in page_info.elements:

                                        # 跳过非视频元素
                                        if not isinstance(element_info, ElementVideo):
                                            continue

                                        # 创建引用
                                        video_id = element_info.video_id

                                        # 上报视频观看行为, 疑似是用来前端防多开
                                        watch_status = parsed_watch_video_behaviors[
                                            video_id
                                        ]

                                        if not watch_status:
                                            logger.warning(
                                                f"[视频][{video_id}] 上报观看行为失败"
                                            )

                                        else:
                                            logger.success(
                                                f"[视频][{video_id}] 上报观看行为成功"
                                            )

                                        # 休眠 0.3s
                                        await asyncio.sleep(0.3)

                        # 为该 节 创建学习记录请求
                        logger.info(f"[节][{section_id}] 开始构造同步学习记录请求")
                        retry = 0
                        while True:
                            # 构造同步学习记录请求
                            study_record_info = (
                                self.data_manager.build_sync_study_record_request(
                                    study_start_time=study_start_time,
                                    section_info=section_info,
                                    user_info=user_info,
                                    study_time_config=self.config.study_time,
                                    is_first=is_first,
                                )
                            )

                            # 构建失败
                            if not study_record_info:
                                logger.warning(f"构建请求信息失败, 跳过")
                                break

                            logger.info(f"[节][{section_id}] 开始上报学习记录")

                            # 上报学习记录
                            sync_status = await self.course_api.sync_study_record(
                                study_record_info=study_record_info
                            )

                            # 重试过多
                            if retry >= 3:
                                logger.warning(
                                    f"[节][{section_id}] 尝试重试上报学习记录失败, 跳过"
                                )
                                break

                            # 上报失败
                            if not sync_status:
                                logger.warning(f"[节][{section_id}] 上报学习记录失败")

                            # 上报成功
                            else:
                                logger.success(f"[节][{section_id}] 上报学习记录成功")
                                break

                            retry += 1
                            await asyncio.sleep(1)

                        # 第二次才冷却
                        if not is_first:
                            # 冷却
                            await asyncio.sleep(self.config.sleep_time)

            if not self.user_config.courses:
                logger.warning("当前用户未配置课程")
                return None

            if not await self.__start_courseware_confirm():
                return None

            user_info = await self.course_api.get_user_info()
            if not user_info:
                logger.warning("获取用户信息失败")
                return None

            # 创建引用
            courses = self.user_config.courses

            # 遍历课程
            for course_id, course_info in courses.items():
                # 创建引用
                class_id = course_info.class_id
                course_name = course_info.course_name
                textbooks = course_info.textbooks

                logger.info(f"[课程][{course_id}] 开始处理 '{course_name}'")
                # 遍历教材
                for textbook_id, textbook_info in textbooks.items():
                    # 创建引用
                    textbook_name = textbook_info.textbook_name
                    chapters = textbook_info.chapters

                    # 第一次处理
                    logger.info(
                        f"[教材][{textbook_id}] 开始第一次处理 '{textbook_name}'"
                    )
                    await courseware_handler(
                        chapters=chapters, user_info=user_info, is_first=True
                    )

                    # 刷新教材信息
                    logger.info(
                        f"[教材][{textbook_id}] 尝试刷新 '{textbook_name}', 可能耗时较长(<30s)"
                    )
                    refresh_status = await self.course_api.textbook_information(
                        course_id=course_id, textbook_id=textbook_id
                    )
                    if refresh_status:
                        logger.success(f"[教材][{textbook_id}] 刷新成功")
                    else:
                        logger.warning(f"[教材][{textbook_id}] 刷新失败")

                    # 第二次处理
                    logger.info(
                        f"[教材][{textbook_id}] 开始第二次处理 '{textbook_name}'"
                    )
                    await courseware_handler(
                        chapters=chapters, user_info=user_info, is_first=False
                    )

            # 删除已完成的课件
            await self.__prune_completed_courseware()
            if self.user_config.courses:
                logger.warning("似乎还有课件没刷完")

            logger.success("刷课流程已结束")

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][COURSEWARE] 刷课过程出现异常: {e}")
            return None

    async def __print_courseware_info(self) -> None:
        """查看刷课信息"""
        logger.debug("[MANAGER][COURSEWARE] 查看刷课信息")

        try:
            if not self.user_config.courses:
                logger.warning("当前用户已配置课程列表为空")
                return None

            print("=" * 100)
            logger.info("当前用户配置的课程信息:")
            # 创建引用
            courses = self.user_config.courses

            # 遍历课程
            for course_id, course_info in courses.items():
                logger.info("")
                logger.info(f"[课程][{course_id}] '{course_info.course_name}'")

                # 创建引用
                textbooks = course_info.textbooks

                # 遍历教材
                for textbook_id, textbook_info in textbooks.items():
                    logger.info("")
                    logger.info(
                        f" [教材][{textbook_id}] '{textbook_info.textbook_name}'"
                    )

                    # 创建引用
                    chapters = textbook_info.chapters

                    # 遍历章节
                    for chapter_id, chapter_info in chapters.items():
                        logger.info("")
                        logger.info(f"   [章] '{chapter_info.chapter_name}'")

                        # 创建引用
                        sections = chapter_info.sections

                        # 遍历节
                        for section_id, section_info in sections.items():
                            logger.info("")
                            logger.info(f"     [节] '{section_info.section_name}'")

                            # 创建引用
                            pages = section_info.pages

                            # 遍历页面
                            for page_id, page_info in pages.items():
                                # 创建引用
                                page_content_type = page_info.page_content_type
                                page_is_complete = page_info.is_complete

                                page_type_map = {
                                    5: "文档/纯文本(Doc/Content)",
                                    6: "视频(Video)",
                                    7: "题目(Question)",
                                }
                                complete_status = (
                                    "已刷完" if page_is_complete else "未完成"
                                )
                                page_type = ""
                                page_text = f"       [{complete_status}][{page_type_map[page_content_type]}] '{page_info.page_name}'"
                                if page_is_complete:
                                    logger.success(page_text)
                                else:
                                    logger.warning(page_text)

            print("=" * 100)
            config_type_choice_map = {
                "question": "题目类型",
                "document": "文档类型",
                "content": "纯文本类型",
            }
            logger.info(f"上报冷却时间: {self.config.sleep_time:.2f} 秒")
            logger.info("当前上报时长配置:")
            for k, v in self.config.study_time.model_dump().items():
                logger.info(
                    f"[{k}] {config_type_choice_map[k]}, 当前值: {v["min"]}~{v["max"]} 秒"
                )
            print("=" * 100)

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][COURSEWARE] 查看刷课信息出错: {e}")
            return None

    async def __remove_courseware(self) -> None:
        """删除课件"""
        logger.debug("[MANAGER][COURSEWARE] 删除课件")

        try:
            # 创建引用
            courses = self.user_config.courses

            # 课程为空
            if not courses:
                logger.warning("当前用户未配置课程")
                return None

            # 提示
            logger.warning(
                "注意, 请在接下来进行操作前确保你理解优学院课件的架构, 例子如下: "
            )
            logger.warning("[课程] -> '形xxx策'")
            logger.warning(" [教材] -> '形xxx策 2025-2026 第一学期'")
            logger.warning("   [章] -> '专题一 全面xxx，深入xxx'")
            logger.warning("     [节] -> '一、全面客观xxx'")
            logger.warning("       [页] -> '1-1关于xxxx'")
            logger.warning("       [页] -> '1-2全面客观xxx（一）'")
            logger.warning("       [页] -> '1-3全面客观xxx（二）'")
            logger.warning("其中, 每一页内有多个元素, 例如 视频元素/题目元素/文档元素")
            logger.warning(
                "因结构过于复杂, CLI不方便实现, 请确保您理解接下来的每一步操作的作用后再进行"
            )
            logger.warning("接下来的操作将以 [页] 为单位进行删除")

            # 获取用户确认
            confirm = await questionary.confirm(
                message="是否确认继续执行课件删除?"
            ).ask_async()

            # 取消
            if not confirm:
                logger.info("已取消删除课件")
                return None

            # 创建课程选择
            course_choices = [
                f"[{course_id}] {course_info.course_name}"
                for course_id, course_info in courses.items()
            ] + ["取消"]

            # 获取用户选择的课程ID列表
            raw_selected_course_ids: list[str] = await answer(
                questionary.checkbox(
                    message="请先选择要删除的课件所在课程",
                    choices=course_choices,
                    validate=lambda x: len(x) > 0 or "不可为空, 请选择",
                    instruction="(使用方向键移动，空格键选择，a键全选/取消，i键反选)",
                )
            )

            if "取消" in raw_selected_course_ids:
                logger.info("已取消删除课件")
                return None

            # 解析课程ID列表
            selected_course_ids = [
                int(course_id.split("]")[0].split("[")[1].strip())
                for course_id in raw_selected_course_ids
            ]

            logger.info(f"[课程] 将要修改 {len(selected_course_ids)} 个课程")

            # 遍历已选中的课程
            for course_id in selected_course_ids:
                # 创建引用
                course_info = courses[course_id]
                course_name = course_info.course_name
                textbooks = course_info.textbooks

                logger.info(f"[课程] 正在处理 '{course_name}'")

                # 创建教材选择
                textbook_choices = [
                    f"[{textbook_id}] {textbook_info.textbook_name}"
                    for textbook_id, textbook_info in textbooks.items()
                ] + ["取消"]

                # 获取用户选择的教材ID列表
                raw_selected_textbook_ids: list[str] = await answer(
                    questionary.checkbox(
                        message="请先选择要删除的课件所在教材",
                        choices=textbook_choices,
                        validate=lambda x: len(x) > 0 or "不可为空, 请选择",
                        instruction="(使用方向键移动，空格键选择，a键全选/取消，i键反选)",
                    )
                )

                if "取消" in raw_selected_textbook_ids:
                    logger.info("已取消删除课件")
                    return None

                # 解析教材ID列表
                selected_textbook_ids = [
                    int(textbook_id.split("]")[0].split("[")[1].strip())
                    for textbook_id in raw_selected_textbook_ids
                ]

                logger.info(f"[教材] 将要修改 {len(selected_textbook_ids)} 个教材")

                # 遍历已选中的教材
                for textbook_id in selected_textbook_ids:
                    # 创建引用
                    textbook_info = textbooks[textbook_id]
                    textbook_name = textbook_info.textbook_name
                    chapters = textbook_info.chapters

                    logger.info(f"[教材] 正在处理 '{textbook_name}'")

                    # 创建章选择
                    chapter_choices = [
                        f"[{chapter_id}] {chapter_info.chapter_name}"
                        for chapter_id, chapter_info in chapters.items()
                    ]

                    # 获取用户选择的章ID列表
                    raw_selected_chapter_ids: list[str] = await answer(
                        questionary.checkbox(
                            message="请选择要删除的课件所在章",
                            choices=chapter_choices,
                            validate=lambda x: len(x) > 0 or "不可为空, 请选择",
                            instruction="(使用方向键移动，空格键选择，a键全选/取消，i键反选)",
                        )
                    )

                    # 解析章ID列表
                    selected_chapter_ids = [
                        int(chapter_id.split("]")[0].split("[")[1].strip())
                        for chapter_id in raw_selected_chapter_ids
                    ]

                    logger.info(f"[章] 将要修改 {len(selected_chapter_ids)} 个章")

                    # 遍历已选中的章
                    for chapter_id in selected_chapter_ids:
                        # 创建引用
                        chapter_info = chapters[chapter_id]
                        chapter_name = chapter_info.chapter_name
                        sections = chapter_info.sections

                        logger.info(f"[章] 正在处理 '{chapter_name}'")

                        # 创建节选择
                        section_choices = [
                            f"[{section_id}] {section_info.section_name}"
                            for section_id, section_info in sections.items()
                        ]

                        # 获取用户选择的节ID列表
                        raw_selected_section_ids: list[str] = await answer(
                            questionary.checkbox(
                                message="请选择要删除的课件所在节",
                                choices=section_choices,
                                validate=lambda x: len(x) > 0 or "不可为空, 请选择",
                                instruction="(使用方向键移动，空格键选择，a键全选/取消，i键反选)",
                            )
                        )

                        # 解析节ID列表
                        selected_section_ids = [
                            int(section_id.split("]")[0].split("[")[1].strip())
                            for section_id in raw_selected_section_ids
                        ]

                        logger.info(f"[节] 将要修改 {len(selected_section_ids)} 个节")

                        # 遍历已选中的节
                        for section_id in selected_section_ids:
                            # 创建引用
                            section_info = sections[section_id]
                            section_name = section_info.section_name
                            pages = section_info.pages

                            logger.info(f"[节] 正在处理 '{section_name}'")

                            # 创建页面选择
                            page_choices = []
                            for page_id, page_info in pages.items():
                                page_is_complete = page_info.is_complete
                                page_complete_status = (
                                    "完成" if page_is_complete else "未完成"
                                )
                                page_choices.append(
                                    f"[{page_complete_status}][{page_id}] {page_info.page_name}"
                                )

                            # 获取用户选择的页面ID列表
                            raw_selected_page_ids: list[str] = await answer(
                                questionary.checkbox(
                                    message="请选择要删除的页面",
                                    choices=page_choices,
                                    validate=lambda x: len(x) > 0 or "不可为空, 请选择",
                                    instruction="(使用方向键移动，空格键选择，a键全选/取消，i键反选)",
                                )
                            )

                            # 解析页面ID列表
                            selected_page_ids = [
                                int(page_id.split("][")[1].split("]")[0].strip())
                                for page_id in raw_selected_page_ids
                            ]

                            logger.warning(
                                f"[页面] 将要删除 {len(selected_page_ids)} 个页面"
                            )

                            # 遍历已选中的页面
                            for page_id in selected_page_ids:
                                # 创建引用
                                page_info = pages[page_id]
                                page_name = page_info.page_name

                                # 删除页面
                                pages.pop(page_id)
                                logger.success(f"已删除页面: {page_name}")

                # 清理空的课件
                courses[course_id].prune()
                if not courses[course_id].textbooks:
                    courses.pop(course_id)

            # 保存配置
            self.config.save()
            await self.__print_courseware_info()
            logger.success("修改课件成功")

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][COURSEWARE] 删除课件: {e}")
            return None

    async def __modify_study_time(self) -> None:
        """修改刷课上报时长"""
        logger.debug("[MANAGER][COURSEWARE] 修改刷课上报时长")

        try:
            while True:
                # 创建引用
                study_time_config = self.config.study_time
                config_type_choice_map = {
                    "question": "题目类型",
                    "document": "文档类型",
                    "content": "纯文本类型",
                }

                # 创建选择项
                config_type_choices = [
                    f"[{k}] {config_type_choice_map[k]}, 当前值: {v["min"]}~{v["max"]} 秒"
                    for k, v in study_time_config.model_dump().items()
                ] + ["返回"]

                # 获取用户选择
                selected_type: str = await answer(
                    questionary.select(
                        message="请选择要修改的学习时长上报类型",
                        choices=config_type_choices,
                        instruction="(使用方向键选择, 回车键确认)",
                    )
                )

                # 返回
                if selected_type == "返回":
                    return None

                # 解析用户选择
                selected_type = selected_type.split("[")[1].split("]")[0].strip()

                # 获取用户输入
                min_time = await answer(
                    questionary.text(
                        message=f"请输入 '{config_type_choice_map[selected_type]}' 学习时长上报的最小时长 (秒)",
                        default="180",
                        validate=lambda x: x.isdigit()
                        and 0 <= int(x) <= 3600
                        or "请输入正确的数字(0~3600)",
                    )
                )

                # 获取用户输入
                max_time = await answer(
                    questionary.text(
                        message=f"请输入 '{config_type_choice_map[selected_type]}' 学习时长上报的最大时长 (秒)",
                        default="360",
                        validate=lambda x: x.isdigit()
                        and int(min_time) <= int(x) <= 3600
                        or f"请输入正确的数字({min_time}~3600)",
                    )
                )

                # 获取对象
                selected_study_minmax_time = getattr(study_time_config, selected_type)
                if not isinstance(
                    selected_study_minmax_time, ConfigModel.StudyTime.MinMaxTime
                ):
                    raise

                # 保存学习时长上报
                selected_study_minmax_time.min = int(min_time)
                selected_study_minmax_time.max = int(max_time)
                self.config.save()

                logger.success(
                    f"成功修改 '{config_type_choice_map[selected_type]}' 学习时长上报时长为 {min_time}~{max_time} 秒"
                )

        except Exception as e:
            logger.error(
                f"{format_exc()}\n[MANAGER][COURSEWARE] 修改刷课上报时长出错: {e}"
            )
            return None

    async def __prune_completed_courseware(self) -> None:
        """清理已刷完课程"""
        logger.debug("[MANAGER][COURSEWARE] 清理已刷完课程")

        try:
            if not self.user_config.courses:
                logger.warning("当前用户未配置课程")
                return None

            logger.info(f"正在重新获取学习记录")

            # 遍历课程
            for course_id, course_info in self.user_config.courses.items():
                # 创建引用
                textbooks = course_info.textbooks

                # 遍历教材
                for textbook_id, textbook_info in textbooks.items():
                    # 创建引用
                    chapters = textbook_info.chapters

                    # 遍历章
                    for chapter_id, chapter_info in chapters.items():
                        # 创建引用
                        chapter_name = chapter_info.chapter_name
                        sections = chapter_info.sections

                        # 收集获取学习记录信息的协程对象列表
                        coros_get_study_record_info = []
                        for section_id, section_info in sections.items():
                            coros_get_study_record_info.append(
                                self.course_api.get_study_record_info(
                                    section_id=section_id
                                )
                            )

                        # 异步调度
                        results_get_study_record_info = await asyncio.gather(
                            *coros_get_study_record_info
                        )

                        # 解析异步调度信息
                        parsed_study_record_infos: dict[
                            int, tuple[bool, StudyRecordAPIResponse | None]
                        ] = {}
                        for result in results_get_study_record_info:
                            for section_id, (
                                status,
                                study_record_info,
                            ) in result.items():
                                parsed_study_record_infos[section_id] = (
                                    status,
                                    study_record_info,
                                )

                        logger.success(
                            f"[章节][{chapter_name}] 获取到 {len(parsed_study_record_infos)} 个学习记录信息"
                        )

                        # 遍历节
                        for section_id, section_info in sections.items():
                            # 创建引用
                            section_name = section_info.section_name
                            resp_status, resp_study_record_info = (
                                parsed_study_record_infos[section_id]
                            )
                            # 跳过获取失败的学习记录
                            if not resp_status:
                                logger.warning(
                                    f"尝试获取学习记录 '{section_name}' 失败, 跳过"
                                )
                                continue

                            # 未学习 跳过
                            if not resp_study_record_info:
                                continue

                            # 解析学习记录信息
                            self.data_manager.parse_study_record_info(
                                course_config=course_info,
                                textbook_id=textbook_id,
                                study_record_info=resp_study_record_info,
                            )

            # 删除已刷完课程
            for course_id, course_info in dict(self.user_config.courses).items():
                course_info.prune(remove_complete=True)
                if not course_info.textbooks:
                    self.user_config.courses.pop(course_id)

            # 保存配置
            self.config.save()
            await self.__print_courseware_info()
            logger.success("成功清理已刷完课程")

        except Exception as e:
            logger.error(
                f"{format_exc()}\n[MANAGER][COURSEWARE] 清理已刷完课程出错: {e}"
            )
            return None

    async def __decrypt_sync_study_record_request(self) -> None:
        """解密同步学习记录请求数据"""
        logger.debug("[MANAGER][COURSEWARE] 解密同步学习记录请求数据")

        try:
            encrypted_text = await answer(
                questionary.text(
                    "请输入: ", validate=lambda x: len(x) > 0 or "请输入内容"
                )
            )

            decrypted_text = sync_text_decrypt(encrypted_text)
            logger.info(
                json.dumps(json.loads(decrypted_text), indent=4, ensure_ascii=False)
            )

        except Exception as e:
            logger.error(
                f"{format_exc()}\n[MANAGER][COURSEWARE] 解密同步学习记录请求数据出错: {e}"
            )
