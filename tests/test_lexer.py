# GHOST FIVE // VECTIS
# Regression coverage for the VECTIS lexer contract.
from unittest import TestCase

from vectis.lexer import (
    KEYWORDS,
    Lexer,
    LexerError,
)
from vectis.source_position import SourcePosition
from vectis.source_span import SourceSpan
from vectis.token import Token


class TestLexer(TestCase):
    def lex(
        self,
        source,
        file="test.vectis",
    ):
        return Lexer(
            source,
            file=file,
        ).tokenize()

    def compact(self, source):
        return [
            (token.type, token.value)
            for token in self.lex(source)
        ]

    def test_reserved_keywords(self):
        source = " ".join(
            sorted(KEYWORDS)
        )

        tokens = self.lex(source)

        self.assertEqual(
            len(tokens),
            len(KEYWORDS),
        )

        self.assertTrue(
            all(
                token.type == "keyword"
                for token in tokens
            )
        )

        self.assertEqual(
            {token.value for token in tokens},
            set(KEYWORDS),
        )

    def test_keyword_matching_is_case_sensitive(self):
        self.assertEqual(
            self.compact(
                "mission Mission source_data"
            ),
            [
                ("keyword", "mission"),
                ("identifier", "Mission"),
                ("identifier", "source_data"),
            ],
        )

    def test_identifiers(self):
        self.assertEqual(
            self.compact(
                "accessible_tools "
                "user_input _data2 Report"
            ),
            [
                (
                    "identifier",
                    "accessible_tools",
                ),
                (
                    "identifier",
                    "user_input",
                ),
                (
                    "identifier",
                    "_data2",
                ),
                (
                    "identifier",
                    "Report",
                ),
            ],
        )

    def test_empty_string(self):
        tokens = self.lex('""')

        self.assertEqual(
            len(tokens),
            1,
        )
        self.assertEqual(
            tokens[0].type,
            "string",
        )
        self.assertEqual(
            tokens[0].value,
            "",
        )

    def test_multiline_string(self):
        tokens = self.lex(
            '"first line\nsecond line"'
        )

        self.assertEqual(
            tokens[0].value,
            "first line\nsecond line",
        )

        self.assertEqual(
            tokens[0].span.start.line,
            1,
        )
        self.assertEqual(
            tokens[0].span.start.column,
            1,
        )
        self.assertEqual(
            tokens[0].span.end.line,
            2,
        )
        self.assertEqual(
            tokens[0].span.end.column,
            12,
        )

    def test_backslash_is_ordinary_string_character(self):
        tokens = self.lex(
            '"a\\b"'
        )

        self.assertEqual(
            tokens[0].value,
            "a\\b",
        )

    def test_integer_and_decimal_numbers(self):
        self.assertEqual(
            self.compact(
                "42 +42 -42 "
                "3.14 +0.5 -0.001"
            ),
            [
                ("number", "42"),
                ("number", "+42"),
                ("number", "-42"),
                ("number", "3.14"),
                ("number", "+0.5"),
                ("number", "-0.001"),
            ],
        )

    def test_numeric_underscore_not_part_of_number(self):
        self.assertEqual(
            self.compact("123_456"),
            [
                ("number", "123"),
                ("identifier", "_456"),
            ],
        )

    def test_malformed_second_decimal_point_errors(self):
        with self.assertRaises(LexerError):
            self.lex("1.2.3")

    def test_comment_is_ignored(self):
        self.assertEqual(
            self.compact(
                "// ignored\nmission"
            ),
            [
                ("keyword", "mission"),
            ],
        )

    def test_trailing_comment_is_ignored(self):
        self.assertEqual(
            self.compact(
                'mission "demo" { '
                "// comment\n}"
            ),
            [
                ("keyword", "mission"),
                ("string", "demo"),
                ("punctuation", "{"),
                ("punctuation", "}"),
            ],
        )

    def test_comment_marker_inside_string_is_text(self):
        tokens = self.lex(
            '"comment // remains text"'
        )

        self.assertEqual(
            tokens[0].value,
            "comment // remains text",
        )

    def test_whitespace_is_ignored(self):
        self.assertEqual(
            self.compact(
                " \tmission\r\n"
                "\t source "
            ),
            [
                ("keyword", "mission"),
                ("keyword", "source"),
            ],
        )

    def test_all_punctuation(self):
        source = "{}()[];,"

        tokens = self.lex(source)

        self.assertEqual(
            [token.type for token in tokens],
            ["punctuation"] * len(source),
        )

        self.assertEqual(
            [token.value for token in tokens],
            list(source),
        )

    def test_all_operators(self):
        self.assertEqual(
            self.compact(
                ">= <= == != "
                "+ - * / && || !"
            ),
            [
                ("operator", ">="),
                ("operator", "<="),
                ("operator", "=="),
                ("operator", "!="),
                ("operator", "+"),
                ("operator", "-"),
                ("operator", "*"),
                ("operator", "/"),
                ("operator", "&&"),
                ("operator", "||"),
                ("operator", "!"),
            ],
        )

    def test_longest_match_operators(self):
        tokens = self.lex(
            ">= <= == != && ||"
        )

        self.assertEqual(
            [token.value for token in tokens],
            [
                ">=",
                "<=",
                "==",
                "!=",
                "&&",
                "||",
            ],
        )

    def test_bare_operator_prefixes_are_errors(self):
        for operator in (
            "=",
            "&",
            "|",
        ):
            with self.subTest(
                operator=operator
            ):
                with self.assertRaises(
                    LexerError
                ):
                    self.lex(operator)

    def test_unrecognized_character_errors(self):
        with self.assertRaises(
            LexerError
        ) as context:
            self.lex("@")

        self.assertIn(
            "test.vectis:1:1",
            str(context.exception),
        )

    def test_unterminated_string_errors_at_opening_quote(self):
        with self.assertRaises(
            LexerError
        ) as context:
            self.lex(
                'mission "unterminated'
            )

        error = context.exception

        self.assertEqual(
            error.line,
            1,
        )
        self.assertEqual(
            error.column,
            9,
        )

    def test_line_and_column_progression(self):
        tokens = self.lex(
            "  mission\n"
            "    source"
        )

        mission = tokens[0]
        source = tokens[1]

        self.assertEqual(
            (
                mission.span.start.line,
                mission.span.start.column,
                mission.span.end.line,
                mission.span.end.column,
            ),
            (1, 3, 1, 9),
        )

        self.assertEqual(
            (
                source.span.start.line,
                source.span.start.column,
                source.span.end.line,
                source.span.end.column,
            ),
            (2, 5, 2, 10),
        )

    def test_comment_advances_source_position(self):
        tokens = self.lex(
            "// comment\n"
            "mission"
        )

        self.assertEqual(
            tokens[0].span.start.line,
            2,
        )
        self.assertEqual(
            tokens[0].span.start.column,
            1,
        )

    def test_source_file_is_preserved(self):
        token = self.lex(
            "mission",
            file="workflow.vectis",
        )[0]

        self.assertEqual(
            token.span.file,
            "workflow.vectis",
        )

    def test_tokens_use_canonical_compiler_types(self):
        token = self.lex(
            "mission"
        )[0]

        self.assertIsInstance(
            token,
            Token,
        )
        self.assertIsInstance(
            token.span,
            SourceSpan,
        )
        self.assertIsInstance(
            token.span.start,
            SourcePosition,
        )

    def test_representative_program_lexes(self):
        source = '''
mission "Research accessibility tools" {
    source web {
        query "accessible developer tools"
    }

    analyze findings {
        require citations
    }

    when confidence >= 0.80 {
        publish report
    }

    otherwise {
        request review
    }
}
'''

        tokens = self.lex(source)

        self.assertGreater(
            len(tokens),
            20,
        )

        self.assertEqual(
            tokens[0].type,
            "keyword",
        )
        self.assertEqual(
            tokens[0].value,
            "mission",
        )

    def test_sign_is_numeric_when_immediately_before_digit(self):
        self.assertEqual(
            self.compact(
                "left +1 right -2"
            ),
            [
                ("identifier", "left"),
                ("number", "+1"),
                ("identifier", "right"),
                ("number", "-2"),
            ],
        )

    def test_sign_is_operator_when_not_before_digit(self):
        self.assertEqual(
            self.compact(
                "left + right - value"
            ),
            [
                ("identifier", "left"),
                ("operator", "+"),
                ("identifier", "right"),
                ("operator", "-"),
                ("identifier", "value"),
            ],
        )
