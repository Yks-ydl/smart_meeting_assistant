import unittest

from services.translation_server import parse_action_items


class TranslationActionParserTest(unittest.TestCase):
    def test_strips_deadline_labels_from_parenthetical_dates(self) -> None:
        text = "- 张三: 完成项目文档 (日期: 周五前)\n- 李四: 安排联调 (截止日期: 下周三)"

        self.assertEqual(
            parse_action_items(text),
            [
                {
                    "task": "完成项目文档",
                    "assignee": "张三",
                    "deadline": "周五前",
                },
                {
                    "task": "安排联调",
                    "assignee": "李四",
                    "deadline": "下周三",
                },
            ],
        )

    def test_ignores_label_only_deadline_placeholders(self) -> None:
        text = "- 王五: 跟进客户反馈 (日期)"

        self.assertEqual(
            parse_action_items(text),
            [
                {
                    "task": "跟进客户反馈",
                    "assignee": "王五",
                    "deadline": None,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()