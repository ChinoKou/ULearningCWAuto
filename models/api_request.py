from pydantic import BaseModel, Field

class SyncStudyRecordAPIRequest(BaseModel):
    """
    同步学习记录API请求数据模型
    url = https://api.ulearning.cn/yws/api/personal/sync
    params = {"courseType": 4, "platform": "PC"}
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
            status: int = 1
            """完成状态 0: 未完成 1: 已完成"""
            recordTime: float
            """已记录的播放了视频的时长"""
            time: float
            """视频长度 = video_length"""
            startEndTimeList: list[StartEndTime]

        class QuestionDTO(BaseModel):
            """问题元素数据模型"""

            questionid: int
            """问题ID = question_id"""
            answerList: list[str]
            """答案列表"""
            score: int
            """分数"""

        pageid: int
        """页面RelationID = page_relation_id"""
        complete: int = 1  # 1
        """完成状态 0: 未完成 1: 已完成"""
        studyTime: int
        """学习时长(s)"""
        score: int
        """分数"""
        answerTime: int = 1  # 1
        """回答次数"""
        submitTimes: int = 0  # 0
        """提交次数"""
        coursepageId: int | None
        """页面ID = page_id"""
        questions: list[QuestionDTO] = Field(default_factory=list)
        videos: list[VideoDTO] = Field(default_factory=list)
        speaks: list = Field(default_factory=list)

    itemid: int
    """节ID = section_id"""
    autoSave: int = 1  # 1
    withoutOld: None = None  # None
    complete: int = 1  # 1
    """完成状态 0: 未完成 1: 已完成"""
    studyStartTime: int
    """初始化返回的时间戳(s)"""
    userName: str
    """姓名 CourseAPIUserInfoAPIResponse 的 name 属性"""
    score: int = 100
    """分数"""
    pageStudyRecordDTOList: list[PageStudyRecordDTO]
