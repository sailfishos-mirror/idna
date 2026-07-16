"""Tests for machine-readable error codes and structured exception attributes."""

import ast
import pickle
import unittest

import idna
import idna.core


class ErrorCodeTests(unittest.TestCase):
    def test_every_error_code_is_raisable(self):
        triggers = {
            idna.ErrorCode.LABEL_TOO_LONG: lambda: idna.alabel("a" * 64),
            idna.ErrorCode.DOMAIN_TOO_LONG: lambda: idna.encode("a" * 300),
            idna.ErrorCode.EMPTY_LABEL: lambda: idna.encode("a..b"),
            idna.ErrorCode.EMPTY_DOMAIN: lambda: idna.encode(""),
            idna.ErrorCode.NOT_NFC: lambda: idna.alabel("e\u0301xample"),
            idna.ErrorCode.HYPHEN_34: lambda: idna.alabel("ab--cd"),
            idna.ErrorCode.HYPHEN_ENDS: lambda: idna.alabel("-abc"),
            idna.ErrorCode.LEADING_COMBINER: lambda: idna.alabel("\u0301abc"),
            idna.ErrorCode.DISALLOWED_CODEPOINT: lambda: idna.alabel("abc\u0141"),
            idna.ErrorCode.INVALID_CONTEXTJ: lambda: idna.alabel("a\u200cb"),
            idna.ErrorCode.INVALID_CONTEXTO: lambda: idna.alabel("a\u00b7b"),
            idna.ErrorCode.BIDI_RULE_1: lambda: idna.alabel("0\u05d0"),
            idna.ErrorCode.BIDI_RULE_2: lambda: idna.alabel("\u05d0a"),
            idna.ErrorCode.BIDI_RULE_3: lambda: idna.check_bidi("\u05d0+"),
            idna.ErrorCode.BIDI_RULE_4: lambda: idna.check_bidi("\u05d0\u06600"),
            idna.ErrorCode.BIDI_RULE_5: lambda: idna.alabel("a\u05d0"),
            idna.ErrorCode.BIDI_RULE_6: lambda: idna.check_bidi("a+", check_ltr=True),
            idna.ErrorCode.BIDI_UNKNOWN_DIRECTIONALITY: lambda: idna.check_bidi("\u0378"),
            idna.ErrorCode.INVALID_ALABEL: lambda: idna.ulabel("xn--"),
            idna.ErrorCode.INVALID_ASCII: lambda: idna.encode(b"\xff"),
            idna.ErrorCode.UTS46_DISALLOWED: lambda: idna.uts46_remap("\u0080"),
        }
        self.assertEqual(set(triggers), set(idna.ErrorCode))
        for expected_code, trigger in triggers.items():
            with self.subTest(code=expected_code):
                with self.assertRaises(idna.IDNAError) as ctx:
                    trigger()
                self.assertIs(ctx.exception.code, expected_code)

    def test_error_code_values_are_unique(self):
        values = [code.value for code in idna.ErrorCode]
        self.assertEqual(len(values), len(set(values)))

    def test_structured_attributes(self):
        with self.assertRaises(idna.InvalidCodepoint) as ctx:
            idna.alabel("abc\u0141")
        err = ctx.exception
        self.assertIs(err.code, idna.ErrorCode.DISALLOWED_CODEPOINT)
        self.assertEqual(err.label, "abc\u0141")
        self.assertEqual(err.codepoint, 0x141)
        self.assertEqual(err.position, 4)
        self.assertIn("U+0141", str(err))
        self.assertIn("position 4", str(err))

    def test_attributes_default_to_none(self):
        err = idna.IDNAError("just a message")
        self.assertIsNone(err.code)
        self.assertIsNone(err.label)
        self.assertIsNone(err.codepoint)
        self.assertIsNone(err.position)
        self.assertEqual(str(err), "just a message")

    def test_message_remains_sole_positional_argument(self):
        with self.assertRaises(idna.IDNAError) as ctx:
            idna.encode("a..b")
        self.assertEqual(ctx.exception.args, ("Empty Label",))

    def test_attributes_survive_pickle(self):
        with self.assertRaises(idna.InvalidCodepoint) as ctx:
            idna.alabel("abc\u0141")
        err = pickle.loads(pickle.dumps(ctx.exception))
        self.assertIs(err.code, idna.ErrorCode.DISALLOWED_CODEPOINT)
        self.assertEqual(err.label, "abc\u0141")
        self.assertEqual(err.codepoint, 0x141)
        self.assertEqual(err.position, 4)
        self.assertEqual(str(err), str(ctx.exception))

    def test_every_raise_site_passes_a_code(self):
        """Guard against new raise sites regressing to code-less exceptions."""
        exception_names = {"IDNAError", "IDNABidiError", "InvalidCodepoint", "InvalidCodepointContext"}
        source_path = idna.core.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        missing = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            func = node.exc.func
            if not (isinstance(func, ast.Name) and func.id in exception_names):
                continue
            if not any(keyword.arg == "code" for keyword in node.exc.keywords):
                missing.append(f"{func.id} at core.py:{node.lineno}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
