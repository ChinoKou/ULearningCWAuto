from pydantic import BaseModel, Field

class ElementVideo(BaseModel):
    """视频元素 数据模型"""

    video_id: int
    video_length: int


class ElementQuestion(BaseModel):
    """问题元素 数据模型"""

    class Question(BaseModel):
        """单个问题数据模型"""

        question_id: int
        question_score: int
        question_content: str
        question_answer_list: list = Field(default_factory=list)

    questions: list[Question] = Field(default_factory=list)


class ElementDocumen(BaseModel):
    """文档元素 数据模型"""

    document_content: str


class ElementContent(BaseModel):
    """文本元素 数据模型"""

    content_content: str


class CoursewarePage(BaseModel):
    """课件第三层-页面 数据模型"""

    page_id: int
    page_relation_id: int
    page_name: str
    page_content_type: int  # 上报体构造方式有关
    """
    5: "Doc/Content",
    6: "Video",
    7: "Question",
    """
    is_complete: bool = False
    elements: list[ElementContent | ElementDocumen | ElementVideo | ElementQuestion] = (
        Field(default_factory=list)
    )


class CoursewareSection(BaseModel):
    """课件第二层-节 数据模型"""

    section_id: int
    section_name: str
    pages: dict[int, CoursewarePage] = Field(default_factory=dict)

    def prune(self) -> None:
        """清理已刷完的页面"""
        for page_id, page in dict(self.pages).items():
            if page.is_complete:
                self.pages.pop(page_id)


class CoursewareChapter(BaseModel):
    """课件第一层-章 数据模型"""

    chapter_id: int
    chapter_name: str
    sections: dict[int, CoursewareSection] = Field(default_factory=dict)

    def prune(self, remove_complete: bool = False) -> None:
        """清理已刷完的节和空节"""
        for section_id, section in dict(self.sections).items():
            if remove_complete:
                section.prune()
            if not section.pages:
                self.sections.pop(section_id)
