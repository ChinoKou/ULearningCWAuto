import random
import time
from traceback import format_exc

from loguru import logger

from models import (
    ChapterInfoAPIResponse,
    ConfigModel,
    CourseAPIUserInfoAPIResponse,
    CoursewareChapter,
    CoursewarePage,
    CoursewareSection,
    ElementContent,
    ElementDocumen,
    ElementQuestion,
    ElementVideo,
    ModelCourse,
    StudyRecordAPIResponse,
    SyncStudyRecordAPIRequest,
    TextbookInfoAPIResponse,
)


class DataManager:
    """数据解析/构造类"""

    def __init__(self) -> None:
        pass

    def parse_textbook_info(
        self, course_config: ModelCourse, textbook_info: TextbookInfoAPIResponse
    ) -> bool:
        """
        解析教材信息

        :param course_config: 课件配置对象
        :type course_config: ModelCourse
        :param textbook_info: 教材信息API响应数据模型
        :type textbook_info: TextbookInfoAPIResponse
        :return: 解析是否成功
        :rtype: bool
        """
        logger.debug("[MANAGER][DATA] 解析教材信息")

        try:
            # 创建引用
            textbook_id = textbook_info.courseid
            course_config_chapters = course_config.textbooks[textbook_id].chapters

            # 遍历该教材的所有章节信息
            for chapter_info in textbook_info.chapters:
                # 创建章节ID和章节名称变量
                chapter_id = chapter_info.nodeid
                chapter_name = chapter_info.nodetitle
                chapter_is_hidden = chapter_info.hide

                # 跳过隐藏章节
                if chapter_is_hidden:
                    logger.info(f"跳过隐藏章节: {chapter_name}")
                    continue

                # 初始化配置文件课件章节对象
                course_config_chapters[chapter_id] = CoursewareChapter(
                    chapter_id=chapter_id,
                    chapter_name=chapter_name,
                )

                # 创建引用
                course_config_sections = course_config_chapters[chapter_id].sections

                # 遍历该章节的所有节列表信息
                for section_info in chapter_info.items:
                    # 创建节ID和节名称和节详细信息变量
                    section_id = section_info.itemid
                    section_name = section_info.title
                    section_is_hidden = section_info.hide

                    # 跳过隐藏节
                    if section_is_hidden:
                        logger.info(f"跳过隐藏节: {section_name}")
                        continue

                    # 初始化配置文件课件节对象
                    course_config_sections[section_id] = CoursewareSection(
                        section_id=section_id,
                        section_name=section_name,
                    )

                    # 创建引用
                    course_config_pages = course_config_sections[section_id].pages

                    # 遍历该节下的所有页面列表信息
                    for page_info in section_info.coursepages:
                        # 创建页面ID和页面名称变量
                        page_id = page_info.id
                        page_relation_id = page_info.relationid
                        page_name = page_info.title
                        page_content_type = page_info.contentType

                        # 初始化配置文件课件页面对象
                        course_config_pages[page_id] = CoursewarePage(
                            page_id=page_id,
                            page_relation_id=page_relation_id,
                            page_name=page_name,
                            page_content_type=page_content_type,
                        )

            logger.debug("[MANAGER][DATA] 教材信息解析成功")
            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][DATA] 解析教材信息出错: {e}")
            return False

    def parse_chapter_info(
        self,
        course_config: ModelCourse,
        textbook_id: int,
        chapter_info: ChapterInfoAPIResponse,
    ) -> bool:
        """
        解析章节信息

        :param course_config: 课件配置对象
        :type course_config: ModelCourse
        :param textbook_id: 教材ID
        :type textbook_id: int
        :param chapter_info: 章节信息API响应数据模型
        :type chapter_info: "ChapterInfoAPIResponse"
        :return: 解析是否成功
        :rtype: bool
        """
        logger.debug("[MANAGER][DATA] 解析章节信息")

        try:
            # 创建引用
            ContentPage = ChapterInfoAPIResponse.ItemDTO.WholePageDTO.ContentPageDTO
            VideoPage = ChapterInfoAPIResponse.ItemDTO.WholePageDTO.VideoPageDTO
            QuestionPage = ChapterInfoAPIResponse.ItemDTO.WholePageDTO.QuestionPageDTO
            DocumentPage = ChapterInfoAPIResponse.ItemDTO.WholePageDTO.DocumentPageDTO
            course_config_textbook = course_config.textbooks[textbook_id]
            chapter_id = chapter_info.chapterid
            course_config_chapter = course_config_textbook.chapters[chapter_id]
            course_config_sections = course_config_chapter.sections

            # 遍历该章节的所有节列表信息
            for section_info in chapter_info.wholepageItemDTOList:
                # 创建引用
                section_id = section_info.itemid
                if section_id not in course_config_sections:
                    continue

                course_config_pages = course_config_sections[section_id].pages

                # 遍历该节下的所有页面列表信息
                for page_info in section_info.wholepageDTOList:
                    # 创建引用
                    page_id = page_info.id
                    page_relation_id = page_info.relationid
                    page_name = page_info.content
                    page_content_type = page_info.contentType
                    course_config_elements = course_config_pages[page_id].elements

                    # 遍历该页面下的所有元素信息
                    for element_info in page_info.coursepageDTOList:
                        # 类型为Doc/Content
                        if page_content_type == 5:
                            # 文档元素
                            if element_info.type == 10 and isinstance(
                                element_info, DocumentPage
                            ):
                                course_config_elements.append(
                                    ElementDocumen(
                                        document_content=element_info.content
                                    )
                                )

                            # 内容元素
                            elif element_info.type == 12 and isinstance(
                                element_info, ContentPage
                            ):
                                course_config_elements.append(
                                    ElementContent(content_content=element_info.content)
                                )

                            # 未知元素
                            else:
                                logger.warning(f"未知的元素类型: {element_info.type}")
                                logger.debug(element_info)

                        # 类型为Video
                        elif page_content_type == 6:
                            # 跳过该页面下非视频元素
                            if not isinstance(element_info, VideoPage):
                                continue

                            # 创建引用
                            video_id = element_info.resourceid
                            video_length = element_info.videoLength

                            # 初始化配置文件课件视频元素对象
                            course_config_elements.append(
                                ElementVideo(
                                    video_id=video_id, video_length=video_length
                                )
                            )

                        # 类型为Question
                        elif page_content_type == 7:
                            # 跳过该页面下非问题元素
                            if not isinstance(element_info, QuestionPage):
                                continue

                            # 初始化问题列表
                            questions: list[ElementQuestion.Question] = []

                            # 遍历问题元素下的所有问题
                            for question_info in element_info.questionDTOList:
                                # 创建引用
                                question_id = question_info.questionid
                                question_score = question_info.score
                                question_content = question_info.title

                                # 初始化配置文件课件问题元素单个问题对象
                                question = ElementQuestion.Question(
                                    question_id=question_id,
                                    question_score=int(question_score),
                                    question_content=question_content,
                                )
                                questions.append(question)

                            # 初始化配置文件课件问题元素对象
                            course_config_elements.append(
                                ElementQuestion(questions=questions)
                            )

            logger.debug(f"[MANAGER][DATA] 解析章节信息成功")
            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][DATA] 解析章节信息出错: {e}")
            return False

    def parse_study_record_info(
        self,
        course_config: ModelCourse,
        textbook_id: int,
        study_record_info: StudyRecordAPIResponse,
    ) -> bool:
        """
        解析学习记录信息

        :param course_config: 课件配置对象
        :type course_config: ModelCourse
        :param textbook_id: 教材ID
        :type textbook_id: int
        :param study_record_info: 学习记录API响应数据模型
        :type study_record_info: StudyRecordAPIResponse
        :return: 解析是否成功
        :rtype: bool
        """
        logger.debug(f"[MANAGER][DATA] 解析学习记录信息")

        try:
            # 创建引用
            chapter_id = study_record_info.node_id
            section_id = study_record_info.item_id
            course_config_textbook = course_config.textbooks[textbook_id]
            course_config_chapter = course_config_textbook.chapters[chapter_id]
            course_config_section = course_config_chapter.sections[section_id]
            course_config_pages = course_config_section.pages

            # 遍历该节下的所有页面信息
            for page_info in study_record_info.pageStudyRecordDTOList:
                page_relation_id = page_info.pageid
                page_is_complete = page_info.complete

                # 遍历配置文件课件对象的所有页面信息以匹配 relation_id
                for course_page_id, course_page_info in course_config_pages.items():
                    if course_page_info.page_relation_id == page_relation_id:
                        # 设置页面完成状态
                        course_page_info.is_complete = bool(page_is_complete)

            logger.debug(f"[MANAGER][DATA] 解析学习记录信息成功")
            return True

        except Exception as e:
            logger.error(f"{format_exc()}\n[MANAGER][DATA] 解析学习记录信息出错: {e}")
            return False

    def build_sync_study_record_request(
        self,
        study_start_time: int,
        section_info: CoursewareSection,
        user_info: CourseAPIUserInfoAPIResponse,
        study_time_config: ConfigModel.StudyTime,
        is_first: bool,
    ) -> SyncStudyRecordAPIRequest | None:
        """
        构造同步学习记录请求

        :param study_start_time: 初始化返回的学习开始时间戳(s)
        :type study_start_time: int
        :param section_info: 节信息
        :type section_info: CoursewareSection
        :param user_info: 获取用户信息API响应数据模型
        :type user_info: CourseAPIUserInfoAPIResponse
        :param study_time_config: 配置文件中的学习时间配置
        :type study_time_config: ConfigModel.StudyTime
        :param is_first: 是否为首次同步学习记录
        :type is_first: bool
        :return: 同步学习记录请求数据模型
        :rtype: SyncStudyRecordAPIRequest | None
        """
        logger.debug(f"[MANAGER][DATA] 构造同步学习记录请求")

        try:
            # 创建引用
            PageStudyRecordDTO = SyncStudyRecordAPIRequest.PageStudyRecordDTO
            VideoDTO = PageStudyRecordDTO.VideoDTO
            StartEndTime = VideoDTO.StartEndTime
            QuestionDTO = PageStudyRecordDTO.QuestionDTO
            section_id = section_info.section_id
            pages = section_info.pages

            # 初始化页面学习记录数据模型列表
            page_study_record_dto_list: list[
                SyncStudyRecordAPIRequest.PageStudyRecordDTO
            ] = []

            # 遍历该节下的所有页面信息
            for page_id, page_info in pages.items():
                # 创建引用
                page_relation_id = page_info.page_relation_id
                page_content_type = page_info.page_content_type
                page_name = page_info.page_name

                logger.info(f"[页面][{page_id}] 正在处理 '{page_name}'")

                # 初始化构造信息
                page_study_time = 0
                page_score = 0
                page_study_record_dto_videos = []
                page_study_record_dto_questions = []

                if not is_first:
                    # 类型为Doc/Content
                    if page_content_type == 5:
                        # 分数为100
                        page_score = 100

                        # 获取元素数量
                        element_num = len(page_info.elements)

                        # 判断页面类型
                        element_is_document = False
                        for element in page_info.elements:
                            if isinstance(element, ElementDocumen):
                                element_is_document = True
                                break

                        # 类型为Doc
                        if element_is_document:
                            # 添加学习时长, 最大时长为3600秒
                            page_study_time += min(
                                random.randint(
                                    study_time_config.document.min,
                                    study_time_config.document.max,
                                )
                                * element_num,
                                3600,
                            )
                            logger.info(f"[文档] 学习 {page_study_time} 秒")

                        # 类型为Content
                        else:
                            # 添加学习时长, 最大时长为3600秒
                            page_study_time += min(
                                random.randint(
                                    study_time_config.content.min,
                                    study_time_config.content.max,
                                )
                                * element_num,
                                3600,
                            )
                            logger.info(f"[纯文本] 学习 {page_study_time} 秒")

                    # 类型为Video
                    elif page_content_type == 6:
                        # 分数为100
                        page_score = 100

                        # 遍历所有元素
                        elements = page_info.elements
                        for element in elements:
                            # 非视频元素跳过
                            if not isinstance(element, ElementVideo):
                                continue

                            # 创建引用
                            video_id = element.video_id
                            video_length = element.video_length

                            # 添加学习时长
                            page_study_time += video_length
                            logger.info(f"[视频][{video_id}] 学习 {video_length} 秒")

                            # 获取视频开始时间戳(s)
                            video_start_time = time.time()
                            # 随机观看时长
                            video_watch_time = video_length - random.uniform(2, 8)

                            # 创建视频数据模型
                            page_study_record_dto_videos.append(
                                VideoDTO(
                                    videoid=video_id,
                                    current=video_watch_time,
                                    recordTime=video_watch_time,
                                    time=video_length,
                                    startEndTimeList=[
                                        StartEndTime(
                                            startTime=int(video_start_time),
                                            endTime=int(
                                                video_start_time + video_watch_time
                                            ),
                                        )
                                    ],
                                )
                            )

                    # 类型为Question
                    elif page_content_type == 7:
                        # 添加学习时长, 最大时长为3600秒
                        page_study_time += min(
                            random.randint(
                                study_time_config.question.min,
                                study_time_config.question.max,
                            ),
                            3600,
                        )
                        logger.info(f"[题目] 学习 {page_study_time} 秒")

                        # 遍历所有元素
                        elements = page_info.elements
                        for element in elements:
                            # 非题目元素跳过
                            if not isinstance(element, ElementQuestion):
                                continue

                            # 遍历所有题目
                            for question in element.questions:
                                # 创建引用
                                question_id = question.question_id
                                answer_list = question.question_answer_list
                                question_score = question.question_score

                                # 添加分数
                                page_score += question_score

                                # 创建题目数据模型
                                page_study_record_dto_questions.append(
                                    QuestionDTO(
                                        questionid=question_id,
                                        answerList=answer_list,
                                        score=question_score,
                                    )
                                )

                    # 未知类型
                    else:
                        logger.warning(f"未知的页面类型: {page_content_type}")
                        continue

                # 创建页面数据模型
                page_study_record_dto_list.append(
                    PageStudyRecordDTO(
                        pageid=page_relation_id,
                        studyTime=(
                            0 if is_first else page_study_time
                        ),  # 首次不上报学习时长
                        score=page_score,
                        coursepageId=(
                            page_id if page_study_record_dto_questions else None
                        ),
                        videos=page_study_record_dto_videos,
                        questions=page_study_record_dto_questions,
                    )
                )

            # 创建同步学习记录API请求数据模型
            return SyncStudyRecordAPIRequest(
                itemid=section_id,
                studyStartTime=study_start_time,
                userName=user_info.name,
                pageStudyRecordDTOList=page_study_record_dto_list,
            )

        except Exception as e:
            logger.error(
                f"{format_exc()}\n[MANAGER][DATA] 构造同步学习记录请求出错: {e}"
            )
            return None
