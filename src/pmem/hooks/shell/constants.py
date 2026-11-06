"""终端命令解析用到的常量与正则：命令名集合、只读名单、重定向/路径/脚本识别模式。纯数据，无依赖。"""
from __future__ import annotations

import re

_NULL_TARGETS = {"$null", "/dev/null", "nul", "&1", "&2"}
# 1> 2> *> &> >| 都算；->、=> 是代码里的箭头。目标可带引号
_REDIRECT = re.compile(r"(?<![-=>])([0-9*&]?)>>?\|?\s*(&\d|'[^']*'|\"[^\"]*\"|[^\s|;&<>]+)")
_STDOUT_FDS = {"", "1", "*", "&"}
_PS_WRITERS = {"set-content", "add-content", "out-file", "new-item", "ni", "clear-content", "remove-item", "ri", "sc",
               "ac"}
_TEE = {"tee", "tee-object"}
# 命令里再套一层终端：powershell -Command "..."、cmd /c "..."、bash -c "..."，以及直接运行的脚本文件
_POWERSHELLS = {"powershell", "pwsh"}
_POSIX_SHELLS = {"bash", "sh", "zsh"}
_SHELL_SCRIPT_SUFFIXES = (".ps1", ".bat", ".cmd", ".sh")
_PS_VALUE_FLAGS = {"-executionpolicy", "-ep", "-windowstyle", "-outputformat", "-inputformat", "-workingdirectory",
                   "-configurationname"}
_MAX_NESTING = 3
# 跟在 pmem search 后面会吞掉输出的管道；输出被丢弃的检索不算查过
_DISCARD_STAGES = {"out-null", "out-file", "set-content", "add-content"}
VARIABLE_PATH = re.compile(r"[$%]|\{")
WILDCARD_PATH = re.compile(r"[*?\[]")
# bash -c、bash -lc、sh -ec：合在一起的短参数里带 c 就是内联命令
_POSIX_INLINE_FLAG = re.compile(r"-[a-zA-Z]*c[a-zA-Z]*")
_RM = {"rm", "del", "erase", "rmdir", "rd"}
_COPY = {"cp", "copy", "copy-item", "cpi"}
_MOVE = {"mv", "move", "move-item", "mi", "rename-item", "rni", "ren"}
_PATH_PARAMS = ("-path", "-literalpath", "-filepath", "-destination")
_SCRIPT_SUFFIXES = (".py", ".js", ".mjs", ".cjs")
_INTERPRETERS = {"python", "python3", "py", "node", "deno"}
# python3.12、python312、python3.11.1：带版本号的解释器不在上面的精确集合里。
# pythonw / python3w 不含在这条里（不是用来跑脚本的控制台入口，也不要当成解释器去读脚本）。
_VERSIONED_PYTHON = re.compile(r"python\d+(\.\d+)*")
_SCRIPT_MAX_BYTES = 200_000
# Node 的 rm( / rename( 只认 fs.xxx( 或 xxxSync(：裸写会误中 norm(、confirm(、pandas 的 df.rename(
_CODE_WRITES = re.compile(
    r"\bopen\([^)\n]{0,200}['\"](?:[wax][bt+]*|r[bt]*\+[bt]*)['\"]|write_text|write_bytes|\.unlink\("
    r"|\b(?:writeFile|appendFile|unlink|rm|rename|copyFile|truncate)Sync\("
    r"|\b(?:fs|fsp|fsPromises|promises)\.(?:writeFile|appendFile|unlink|rm|rename|copyFile|truncate)\("
    r"|\bcreateWriteStream\("
    r"|os\.(?:remove|rename|replace)\(|shutil\.(?:copy\w*|move|rmtree)\(|WriteAll\w+|AppendAll\w+"
)
_PATH_LITERAL = re.compile(r"['\"]([^'\"\s]*[/\\][^'\"\s]*|[^'\"\s/\\]+\.\w{1,8})['\"]")
_DOTNET_WRITE = re.compile(r"\[(?:System\.)?IO\.File\]::(?:WriteAll\w+|AppendAll\w+|Delete|Copy|Move)\(\s*['\"]([^'\"]+)",
                           re.IGNORECASE)
_PATCH_FILE = re.compile(r"^(?:\+\+\+ b|--- a)/(\S+)", re.MULTILINE)
# here-string（@' ... '@）与 heredoc（<<EOF ... EOF）的正文是数据，不是要执行的命令。
# 用正则找开头、用字符串查找结束符：整段正则在结束符缺失时是平方级，几十 KB 的命令要几十秒
_HERE_STRING_OPEN = re.compile(r"@(['\"])[ \t]*\r?\n")
_HEREDOC_OPEN = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1([^\n]*)\n")
_MAX_HEREDOCS = 20
# 超过这个长度的命令不逐段解析，直接走执行前后的快照比对
MAX_PARSED_COMMAND = 64_000
_CD = {"cd", "chdir", "set-location", "sl", "pushd", "push-location"}
_POPD = {"popd", "pop-location"}
# 只读命令：命令行里只有这些时不需要执行前后比对文件
_READ_ONLY = {
    "ls", "dir", "gci", "get-childitem", "cat", "type", "gc", "get-content", "head", "tail", "less", "more",
    "rg", "grep", "findstr", "select-string", "sls", "find", "where", "where.exe", "which", "get-command",
    "echo", "write-output", "write-host", "pwd", "get-location", "test-path", "get-item", "gi", "resolve-path",
    "select-object", "select", "sort-object", "sort", "measure-object", "measure", "format-table", "ft",
    "format-list", "fl", "out-string", "where-object", "?", "group-object", "wc",
    "get-date", "get-process", "env", "printenv", "date", "whoami", "hostname", "tree", "stat", "file",
    *_CD, *_POPD, "exit", "true", "false", "sleep", "start-sleep", "clear", "cls",
}
_GIT_READ_ONLY = {"status", "log", "diff", "show", "blame", "branch", "rev-parse", "ls-files", "ls-tree", "grep",
                  "remote", "describe", "shortlog", "cat-file", "reflog", "help", "version", "fetch"}
_SVN_READ_ONLY = {"status", "st", "stat", "log", "diff", "di", "info", "cat", "list", "ls", "blame", "praise",
                  "annotate", "ann", "propget", "pg", "proplist", "pl", "help", "?", "h", "--version"}
_PMEM_READ_ONLY = {"search", "graph", "list", "terms", "doctor", "report", "compact", "scan", "--help", "-h"}
# pmemw 是 Hook 用的无控制台入口；MCP 仍用 pmem。终端里两者等价
_PMEM_CLI = {"pmem", "pmemw"}
# 只改变后面命令运行方式的前缀（sudo rm x 真正执行的是 rm），值为会吞掉下一个参数的选项
_PREFIXES = {
    "sudo": {"-u", "-g", "-p", "-C", "-D", "-U", "-h", "-r", "-t"}, "doas": {"-u", "-C"},
    "env": {"-u", "-C", "--unset", "--chdir"}, "command": set(), "builtin": set(),
    "nohup": set(), "exec": {"-a"}, "time": {"-f", "-o", "--format", "--output"}, "nice": {"-n"},
    "stdbuf": {"-i", "-o", "-e"},
}
_RENAME = {"rename-item", "rni", "ren", "rename"}
# PowerShell 写文件命令里带值的参数；其余以 - 开头的是开关（-Recurse、-Force），不会吞掉后面的路径
_PS_VALUE_PARAMS = {"-value", "-encoding", "-itemtype", "-type", "-name", "-filter", "-include", "-exclude",
                    "-inputobject", "-stream", "-width", "-target", "-credential", "-newname", "-variable",
                    # 通用参数：值是动作名或变量名，不是路径
                    "-erroraction", "-ea", "-warningaction", "-wa", "-informationaction", "-infa",
                    "-errorvariable", "-ev", "-warningvariable", "-wv", "-informationvariable", "-iv",
                    "-outvariable", "-ov", "-outbuffer", "-ob", "-pipelinevariable", "-pv"}
# 第二个位置参数是写入内容而不是路径（Tee-Object 的第一个位置参数是文件，-Variable 时不写文件）
_PS_CONTENT_WRITERS = {"set-content", "sc", "add-content", "ac", "out-file", "tee-object"}
_MAX_ORDERED_STATEMENTS = 40
# 检索之后靠这些连接符接着执行的语句才算“查过再写”；|| 只在检索失败时执行，& 是并行
_SEQUENTIAL_OPS = {"&&", ";", "\n", "\r"}
# 只读命令里能写文件或执行任意程序的选项
_FIND_WRITES = ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls")
_PIPED_ITEMS = _RM | _COPY | _MOVE | {"remove-item", "ri", "clear-content"}
# 以这些程序开头时，pmem 可以出现在它们的参数之后（如 uv run --extra embed pmem record）
_LAUNCHERS = {"uv", "uvx", "pipx", "python", "python3", "py"}


def is_interpreter(name: str) -> bool:
    """python、python3、py、node、deno，以及 python3.12 这种带版本号的名字。调用方已去掉目录和 .exe。"""
    return name in _INTERPRETERS or _VERSIONED_PYTHON.fullmatch(name) is not None


def is_launcher(name: str) -> bool:
    """uv / py / python3.12 只是后面那条命令的启动方式（python3.12 -m pmem search 仍是 pmem）。"""
    return name in _LAUNCHERS or _VERSIONED_PYTHON.fullmatch(name) is not None
