from traceback import format_exc
from typing import Annotated, Literal, Self

from loguru import logger
from pydantic import BaseModel, Discriminator, Field


class BaseAPIResponse(BaseModel):
    """API响应数据模型基类"""

    @classmethod
    def parse(cls, resp_body: dict) -> Self | None:
        """
        解析API响应数据

        :param resp_body: 响应体
        :type resp_body: dict
        :return: 数据模型
        :rtype: Self | None
        """
        try:
            # 尝试验证模型
            return cls.model_validate(obj=resp_body, extra="forbid")

        except Exception as e:
            logger.debug(f"{format_exc()}\n[MODEL] 解析失败")
            logger.warning(f"解析数据过程出错, 尝试兼容多余字段")

            # 尝试兼容多余字段
            return cls.__try_extra(resp_body)

    @classmethod
    def __try_extra(cls, resp_body: dict) -> Self | None:
        """
        解析API响应数据(兼容多语字段)

        :param resp_body: 响应体
        :type resp_body: dict
        :return: 数据模型
        :rtype: Self | None
        """
        try:
            model_instance = cls.model_validate(obj=resp_body, extra="allow")
            logger.success("兼容多余字段成功")
            return model_instance

        except Exception as e:
            logger.error(f"数据解析失败, 请提供日志并且提交issue反馈")
            logger.debug(f"{format_exc()}\n[MODEL] 解析失败")
            return None


class QuestionAnswerAPIResponse(BaseAPIResponse):
    """
    问题答案API响应数据模型
    url = https://api.ulearning.cn/questionAnswer/{question_id}
    params = {"parentId": page_id} 页面ID
    """

    questionid: int
    """问题ID = question_id"""
    correctreply: str
    correctAnswerList: list[str]
    """正确答案列表 与 answer_list 性质相同"""


class StudyRecordAPIResponse(BaseAPIResponse):
    """
    学习记录API响应数据模型
    url = https://api.ulearning.cn/studyrecord/item/{section_id}
    """

    class PageStudyRecordDTO(BaseModel):
        """页面学习记录数据模型"""

        class VideoDTO(BaseModel):
            """视频元素数据模型"""

            class StartEndTime(BaseModel):
                """开始结束时间数据模型"""

                startTime: int
                """开始看视频时间戳(s)"""
                endTime: int
                """结束看视频时间戳(s)"""

            videoid: int
            """视频ID = video_id"""
            current: float
            """当前播放视频的进度"""
            status: int
            recordTime: int
            """已记录的播放了视频的时长"""
            time: float
            """视频长度 = video_length"""
            startEndTimeList: list[StartEndTime | None]

        class QuestionDTO(BaseModel):
            """问题元素数据模型"""

            questionid: int
            """问题ID = question_id"""
            answerList: list[str]
            """答案列表 = answer_list"""
            score: int
            """分数"""

        pageid: int
        """页面RelationID = page_relation_id"""
        complete: int
        """完成状态 0: 未完成 1: 已完成"""
        submitTimes: int
        studyTime: int
        """学习时长"""
        answerTime: int
        """回答次数"""
        videos: list[VideoDTO] | None = None
        questions: list[QuestionDTO] | None = None
        coursepageId: int | None = None
        """与题目(questions)一起出现 为元素ID"""

    completion_status: int
    """完成状态 0: 未完成 1: 已完成"""
    learner_id: int
    """用户ID = user_id"""
    learner_name: str
    """姓名"""
    relationid: int
    """未知ID"""
    customized: int
    activity_title: str
    """节名 section_name"""
    item_id: int
    """节ID = section_id"""
    node_id: int
    """章节ID = chapter_id = nodeid"""
    score: int
    """分数, 为题目时和题目自带的分数有关"""
    studyTime: int
    """学习时长, pageStudyRecordDTOList下所有页面学习时长之和"""
    pageStudyRecordDTOList: list[PageStudyRecordDTO]


class ChapterInfoAPIResponse(BaseAPIResponse):
    """
    章节信息API响应数据模型
    url = https://api.ulearning.cn/wholepage/chapter/stu/{chapter_id}
    哪个神人写的api(
    """

    class ItemDTO(BaseModel):
        """节数据模型"""

        class WholePageDTO(BaseModel):
            """页面数据模型"""

            class BasePageDTO(BaseModel):
                """元素基数据模型"""

                coursepageDTOid: int
                """元素ID = element_id"""
                # type: int
                """
                元素类型
                6: "Question",
                4: "Video",
                10: "Document",
                12: "Content",
                """
                parentid: int
                """页面ID = page_id"""
                orderIndex: int
                resourceid: int
                """资源ID / 视频ID"""
                skipVideoTitle: int
                note: str
                resourceFullurl: str | None = None

            class ContentPageDTO(BasePageDTO):
                """内容元素数据模型"""

                type: Literal[12]
                content: str
                """内容"""

                resourceDTOList: list

            class VideoPageDTO(BasePageDTO):
                """视频元素数据模型"""

                type: Literal[4]
                videoLength: int
                """视频长度 = video_length"""
                resourceid: int
                """视频ID = video_id"""

                resourceContentSize: int
                videoQuestionDTOList: list
                knowledgeResourceDTOS: list
                videoCover: str | None = None
                srtDTO: dict | None = None

            class QuestionPageDTO(BasePageDTO):
                """问题元素数据模型"""

                class QuestionDTO(BaseModel):
                    """题目数据模型"""

                    class choiceitemModel(BaseModel):
                        choiceitemid: int
                        questionid: int
                        title: str

                    questionid: int
                    """问题ID = question_id"""
                    score: float
                    """分数 = question_score"""
                    title: str
                    """问题名 = question_content"""

                    type: int
                    """
                    问题类型
                    1: "单选题",
                    2: "多选题",
                    4: "判断题",
                    """
                    iscontent: int
                    hardlevel: int
                    parentid: int
                    createtime: str
                    updatetime: str
                    remark: str
                    userid: int
                    orgid: int
                    isShare: int
                    blankOrder: int
                    choiceitemModels: list[choiceitemModel] | None = None
                    tagList: list
                    link: str | None = None
                    linkList: list | None = None
                    linkOptionList: dict | None = None
                    relatedTextbookChapterDTOList: list

                type: Literal[6]
                content: str
                answertime: int | None = None
                questionDTOList: list[QuestionDTO]

            class DocumentPageDTO(BasePageDTO):
                """文档数据模型"""

                type: Literal[10]
                content: str
                """内容"""

                resourceContentSize: int
                docTitle: str
                docSize: int
                knowledgeResourceDTOS: list

            id: int
            """页面ID = page_id"""
            relationid: int
            """页面RelationID = page_relation_id"""
            content: str
            """页面名 = page_name = title"""
            contentType: int
            """页面类型 = content_type"""

            contentnodeid: int
            """节ID = section_id"""
            type: int
            orderindex: int
            lastmodifydate: str
            share: int
            status: int
            qrcode: int

            coursepageDTOList: list[
                Annotated[
                    ContentPageDTO | DocumentPageDTO | VideoPageDTO | QuestionPageDTO,
                    Field(discriminator=Discriminator("type")),
                ]
            ]
            """元素列表"""

        itemid: int
        """节ID = section_id = itemid"""
        wholepageDTOList: list[WholePageDTO]
        """页面列表"""

    chapterid: int
    """章节ID = chapter_id = nodeid"""
    wholepageItemDTOList: list[ItemDTO]
    """节列表"""


class TextbookInfoAPIResponse(BaseAPIResponse):
    """
    教材信息API响应数据模型
    url = https://api.ulearning.cn/course/stu/{textbook_id}/directory"
    params = {"classId": class_id}
    """

    class Chapter(BaseModel):
        class Item(BaseModel):
            class CoursePage(BaseModel):
                id: int
                """页面ID = page_id"""
                relationid: int
                """页面RelationID = page_relation_id"""
                title: str
                """页面名 = page_name"""
                orderindex: int
                contentType: int
                """页面类型 = content_type"""

            itemid: int
            """节ID = section_id"""
            title: str
            """节名 = section_name"""
            orderindex: int

            hide: int = Field(default=0)
            """0: 显示，1: 隐藏"""
            ishidepreview: str = Field(default="2")  # 疑似与 hide 互斥出现
            id: int = Field(default=0)  # 当父chapter中出现id时这个也会跟着出现
            """未知ID"""

            coursepages: list[CoursePage]

        nodeid: int
        """章节ID = chapter_id = node_id"""
        nodetitle: str
        """章节名 = chapter_name"""
        orderindex: int

        hide: int = Field(default=0)
        """0: 显示，1: 隐藏"""
        preview: int = Field(default=0)  # 疑似与 hide 互斥出现
        id: int = Field(default=0)
        """未知ID"""

        items: list[Item]
        """节列表"""

    courseid: int
    """教材ID = textbook_id"""
    coursename: str
    """教材名 = textbook_name"""
    chapters: list[Chapter]
    """章列表"""


class TextbookListAPIResponse(BaseAPIResponse):
    """
    教材列表API响应数据模型
    url = https://courseapi.ulearning.cn/textbook/student/{course_id}/list
    """

    class TextbookInfo(BaseModel):
        courseId: int
        """教材ID = textbook_id"""
        name: str
        """教材名 = textbook_name"""

        type: int
        status: int
        limit: int
        author: str | None = None
        copyright: str | None = None
        description: str | None = None
        """描述"""
        cover: str | None = None
        """封面"""
        needapprove: str
        lastModifyDate: int
        """最后修改时间戳"""
        openCourse: int
        md5: str

    textbooks: list[TextbookInfo]


class CourseListAPIResponse(BaseAPIResponse):
    """
    课程列表API响应数据模型
    url = https://courseapi.ulearning.cn/courses/students
    payload = {
        "keyword": "",
        "publishStatus": 1,
        "type": 1,
        "pn": 1,  # page_number
        "ps": 999,  # page_size
        "lang": "zh",
    }
    """

    class _Course(BaseModel):
        id: int
        """课程ID = course_id"""
        name: str
        """课程名 = course_name"""
        classId: int
        """班级ID = class_id"""
        classUserId: int
        """班级用户ID = class_user_id"""

        cover: str
        """课程封面"""
        courseCode: str
        """课程编号"""
        type: int
        className: str
        """班级名"""
        status: int
        """状态"""
        teacherName: str
        """教师名"""
        learnProgress: int
        totalDuration: int
        publishStatus: int
        creatorOrgId: int
        """创建者机构ID"""
        creatorOrgName: str
        """创建者机构名"""

    pn: int
    """页码 = page_number"""
    ps: int
    """页大小 = page_size"""
    total: int
    """总数"""
    courseList: list[_Course]


class LoginAPIUserInfoResponse(BaseAPIResponse):
    """
    登录获取的用户信息API响应模型
    url = https://courseapi.ulearning.cn/users/login/v2
    payload = {
        "loginName": self.user_config.username,
        "password": self.user_config.password,
    }
    """

    orgName: str
    """机构名"""
    headimage: str | None = None
    """头像"""
    roleId: int
    """角色ID"""
    sex: str | None = None
    """性别"""
    orgHome: str
    """机构主页"""
    orgLogo: str
    """机构Logo"""
    userId: int
    """用户ID"""
    orgId: int
    """机构ID"""
    authorization: str
    """鉴权令牌"""
    studentId: str
    """学号"""
    loginName: str
    """登录用户名"""
    name: str
    """姓名"""
    uversion: int
    """优学院版本"""


class CourseAPIUserInfoAPIResponse(BaseAPIResponse):
    """
    获取用户信息API响应数据模型
    url = https://api.ulearning.cn/user
    """

    userid: int
    """用户ID"""
    name: str
    """姓名"""
    headimage: str | None = None
    """头像"""
    orgid: int
    """机构ID"""
    logo: str | None = None
    """机构Logo"""
    roleid: int
    """角色ID"""
    antiCheat: int
    antiDrag: int
    openCourseResource: int
    enableSubtitle: int
    enableSkipVideoTitle: int
