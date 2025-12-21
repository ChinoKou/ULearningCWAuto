from pydantic import BaseModel, Field
from .courseware import CoursewareChapter

class ModelTextbook(BaseModel):
    """课程教材数据模型"""

    textbook_id: int
    textbook_name: str
    status: int
    limit: int
    chapters: dict[int, CoursewareChapter] = Field(default_factory=dict)

    def prune(self, remove_complete: bool = False) -> None:
        """清理已刷完的章"""
        for chapter_id, chapter in dict(self.chapters).items():
            chapter.prune(remove_complete)
            if not chapter.sections:
                self.chapters.pop(chapter_id)


class ModelCourse(BaseModel):
    """课程数据模型"""

    course_id: int
    course_name: str
    class_id: int
    class_user_id: int
    textbooks: dict[int, ModelTextbook] = Field(default_factory=dict)

    def prune(self, remove_complete: bool = False) -> None:
        """清理已刷完的教材和空教材"""
        for textbook_id, textbook in dict(self.textbooks).items():
            textbook.prune(remove_complete)
            if not textbook.chapters:
                self.textbooks.pop(textbook_id)
