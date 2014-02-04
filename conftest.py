###############################################################################
#
# Simple py.test hooks to enable execution and collection of C unit tests.
#
# Copyright 2014, John McNamara, jmcnamara@cpan.org
#
import subprocess
import pytest


def pytest_collect_file(parent, path):
    """
    A hook into py.test to collect test_*.c test files.

    """
    if path.ext == ".c" and path.basename.startswith("test"):
        return CTestFile(path, parent)


class CTestFile(pytest.File):
    """
    A custom file handler class for C unit test files.

    """

    def collect(self):
        """
        Overridden collect method to collect the results from each
        C unit test executable.

        """

        test_exe = str(self.fspath)[0:-2]
        test_output = subprocess.check_output(test_exe)

        lines = test_output.split("\n")
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line.startswith("[")]

        test_results = []
        for line in lines:
            token, data = line.split(" ", 1)
            token = token[1:-1]

            if token in ("PASS", "FAIL"):
                function_name, line_number = data.split(":")
                test_results.append({"condition": token,
                                     "function_name": function_name,
                                     "line_number": int(line_number),
                                     })
            elif token in ("EXP", "GOT", "TST"):
                test_results[-1][token] = data

        for test_result in test_results:
            yield CTestItem(test_result["function_name"], self, test_result)


class CTestItem(pytest.Item):
    """
    Pytest.Item subclass to handle each test result item. There may be
    more than one test result from a test function.

    """

    def __init__(self, name, parent, test_result):
        """Overridden constructor to pass test results dict."""
        super(CTestItem, self).__init__(name, parent)
        self.test_result = test_result

    def runtest(self):
        """The test has already been run. We just evaluate the result."""
        if self.test_result["condition"] == "FAIL":
            raise CTestException(self, self.name)

    def repr_failure(self, excinfo):
        """
        Called when runtest() raises an exception. The method is used
        to format the output of the failed test result.

        """
        if isinstance(excinfo.value, CTestException):
            return ("Test failed : {TST} at {function_name}:{line_number}\n"
                    "         got: {GOT}\n"
                    "    expected: {EXP}\n".format(**self.test_result))

    def reportinfo(self):
        """"Called to display header information about the test case."""
        return self.fspath, self.test_result["line_number"] - 1, self.name


class CTestException(Exception):
    """Custom exception to distinguish C unit test failures from others."""
    pass
