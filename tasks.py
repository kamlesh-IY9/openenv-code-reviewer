"""
Task Definitions for Code Reviewer Environment.
Contains 3 tasks with increasing difficulty:
- Easy: Syntax errors (syntax_check)
- Medium: Logic bugs (logic_bug_detection)
- Hard: Security vulnerabilities (security_audit)
"""

from models import TaskConfig, CodeIssue, IssueType, Severity, CodeSnippet


# Task 1: Easy - Syntax Errors
SYNTAX_CHECK_TASK = TaskConfig(
    name="syntax_check",
    description="""
Review the Python code snippet and identify all syntax errors.
Look for missing colons, unmatched parentheses, incorrect indentation,
and other syntax issues that would prevent the code from running.
Report each issue with its line number, type, and a suggested fix.
""",
    difficulty="easy",
    code_snippet=CodeSnippet(
        language="python",
        filename="data_processor.py",
        code='''def process_data(data)
    result = []
    for item in data
        if item > 0
            result.append(item * 2
        else:
            result.append(0
    return result

def validate_input(user_input)
    if len(user_input > 10
        return False
    return True''',
        context="Simple data processing functions with syntax errors",
    ),
    expected_issues=[
        CodeIssue(
            line_number=1,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.HIGH,
            description="Missing colon at end of function definition",
            suggested_fix="def process_data(data):",
        ),
        CodeIssue(
            line_number=3,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.HIGH,
            description="Missing colon after for loop condition",
            suggested_fix="for item in data:",
        ),
        CodeIssue(
            line_number=4,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.HIGH,
            description="Missing colon after if condition",
            suggested_fix="if item > 0:",
        ),
        CodeIssue(
            line_number=5,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.CRITICAL,
            description="Unclosed parenthesis in append call",
            suggested_fix="result.append(item * 2)",
        ),
        CodeIssue(
            line_number=7,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.CRITICAL,
            description="Unclosed parenthesis in append call",
            suggested_fix="result.append(0)",
        ),
        CodeIssue(
            line_number=10,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.HIGH,
            description="Missing colon at end of function definition",
            suggested_fix="def validate_input(user_input):",
        ),
        CodeIssue(
            line_number=11,
            issue_type=IssueType.SYNTAX_ERROR,
            severity=Severity.CRITICAL,
            description="Unclosed parenthesis in len() call",
            suggested_fix="if len(user_input) > 10:",
        ),
    ],
    hints=[
        "Check all function definitions for missing colons",
        "Look for unclosed parentheses in function calls",
        "Verify all control flow statements (if, for, while) have colons",
    ],
    max_steps=15,
)


# Task 2: Medium - Logic Bugs
LOGIC_BUG_TASK = TaskConfig(
    name="logic_bug_detection",
    description="""
Review the Python code for logic bugs that cause incorrect behavior.
The code may run without syntax errors but produce wrong results.
Look for off-by-one errors, incorrect comparisons, infinite loops,
uninitialized variables, and incorrect algorithm implementations.
""",
    difficulty="medium",
    code_snippet=CodeSnippet(
        language="python",
        filename="shopping_cart.py",
        code='''class ShoppingCart:
    def __init__(self):
        self.items = []
        self.discount = 0
    
    def add_item(self, name, price, quantity):
        self.items.append({
            'name': name,
            'price': price,
            'quantity': quantity
        })
    
    def apply_discount(self, percent):
        self.discount = percent / 100
    
    def calculate_total(self):
        total = 0
        for item in self.items:
            total += item['price'] * item['quantity']
        
        # Apply discount
        if self.discount > 0:
            total = total - self.discount
        
        return total
    
    def get_item_count(self):
        count = 0
        for item in self.items:
            count += 1
        return count
    
    def find_item(self, name):
        for item in self.items:
            if item['name'] = name:
                return item
        return None''',
        context="Shopping cart implementation with logic bugs",
    ),
    expected_issues=[
        CodeIssue(
            line_number=20,
            issue_type=IssueType.LOGIC_BUG,
            severity=Severity.HIGH,
            description="Discount applied incorrectly - subtracting percentage instead of percentage of total",
            suggested_fix="total = total * (1 - self.discount)",
        ),
        CodeIssue(
            line_number=26,
            issue_type=IssueType.LOGIC_BUG,
            severity=Severity.MEDIUM,
            description="Inefficient item counting - should use len(self.items) instead of loop",
            suggested_fix="return len(self.items)",
        ),
        CodeIssue(
            line_number=31,
            issue_type=IssueType.LOGIC_BUG,
            severity=Severity.CRITICAL,
            description="Assignment operator (=) used instead of comparison (==) in if condition",
            suggested_fix="if item['name'] == name:",
        ),
    ],
    hints=[
        "Check how discount is being applied - is it calculating correctly?",
        "Look for places where assignment (=) might be confused with comparison (==)",
        "Consider if there are more efficient ways to count items",
    ],
    max_steps=18,
)


# Task 3: Hard - Security Vulnerabilities
SECURITY_AUDIT_TASK = TaskConfig(
    name="security_audit",
    description="""
Perform a security audit on this Python web application code.
Identify security vulnerabilities including SQL injection, XSS,
command injection, hardcoded secrets, insecure deserialization,
and improper authentication/authorization.
This is critical production code - be thorough!
""",
    difficulty="hard",
    code_snippet=CodeSnippet(
        language="python",
        filename="user_api.py",
        code='''import sqlite3
import os
import pickle
import hashlib
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
DB_PATH = "users.db"
API_KEY = "sk-live-1234567890abcdef"

def get_db():
    return sqlite3.connect(DB_PATH)

@app.route('/api/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Authenticate user
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    
    if user:
        response = make_response(jsonify({"success": True, "user": user[1]}))
        response.set_cookie('session', user[3], httponly=False)
        return response
    else:
        return jsonify({"success": False}), 401

@app.route('/api/user/<user_id>')
def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT id, username, email FROM users WHERE id = " + user_id
    cursor.execute(query)
    user = cursor.fetchone()
    
    if user:
        return jsonify({
            "id": user[0],
            "username": user[1],
            "email": user[2]
        })
    return jsonify({"error": "User not found"}), 404

@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    data = request.get_data()
    profile = pickle.loads(data)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET bio=? WHERE id=?",
        (profile['bio'], profile['user_id'])
    )
    conn.commit()
    
    return jsonify({"success": True})

@app.route('/api/backup', methods=['POST'])
def backup():
    filename = request.json.get('filename')
    os.system(f"tar -czf backups/{filename}.tar.gz data/")
    return jsonify({"success": True, "backup": filename})

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    return f''
<!DOCTYPE html>
<html>
<body>
    <h1>Search Results for: {query}</h1>
</body>
</html>
''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')''',
        context="Flask web API with security vulnerabilities",
    ),
    expected_issues=[
        CodeIssue(
            line_number=7,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.CRITICAL,
            description="Hardcoded API key in source code - should use environment variables",
            suggested_fix="API_KEY = os.environ.get('API_KEY')",
        ),
        CodeIssue(
            line_number=17,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.CRITICAL,
            description="SQL Injection vulnerability - user input directly interpolated into SQL query",
            suggested_fix="Use parameterized queries: cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))",
        ),
        CodeIssue(
            line_number=22,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.HIGH,
            description="Plaintext password storage - passwords should be hashed",
            suggested_fix="Use bcrypt or Argon2 for password hashing",
        ),
        CodeIssue(
            line_number=24,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.MEDIUM,
            description="Session cookie without HttpOnly flag - vulnerable to XSS theft",
            suggested_fix="response.set_cookie('session', user[3], httponly=True, secure=True, samesite='Lax')",
        ),
        CodeIssue(
            line_number=32,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.CRITICAL,
            description="SQL Injection in user lookup - user_id concatenated into query",
            suggested_fix="cursor.execute('SELECT id, username, email FROM users WHERE id = ?', (user_id,))",
        ),
        CodeIssue(
            line_number=46,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.CRITICAL,
            description="Insecure deserialization - pickle.loads on untrusted data allows RCE",
            suggested_fix="Use JSON instead of pickle: profile = request.get_json()",
        ),
        CodeIssue(
            line_number=57,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.CRITICAL,
            description="Command injection - user input passed directly to os.system()",
            suggested_fix="Use subprocess with proper validation: subprocess.run(['tar', '-czf', f'backups/{secure_filename}.tar.gz', 'data/'])",
        ),
        CodeIssue(
            line_number=63,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.HIGH,
            description="Reflected XSS vulnerability - user input rendered without sanitization",
            suggested_fix="Use template engine with auto-escaping: return render_template('search.html', query=escape(query))",
        ),
        CodeIssue(
            line_number=73,
            issue_type=IssueType.SECURITY_VULNERABILITY,
            severity=Severity.MEDIUM,
            description="Debug mode enabled in production - exposes sensitive information",
            suggested_fix="app.run(debug=False, host='127.0.0.1')",
        ),
    ],
    hints=[
        "Look for any hardcoded secrets or credentials",
        "Check all SQL queries - are they using parameterized queries?",
        "Examine how user input is handled - could it lead to code execution?",
        "Review cookie settings - are security flags set properly?",
        "Check for XSS vulnerabilities where user input is rendered",
    ],
    max_steps=25,
)


# Task registry
TASKS = {
    "syntax_check": SYNTAX_CHECK_TASK,
    "logic_bug_detection": LOGIC_BUG_TASK,
    "security_audit": SECURITY_AUDIT_TASK,
}


def get_task_names() -> list:
    """Get list of available task names."""
    return list(TASKS.keys())


def get_task_difficulty(task_name: str) -> str:
    """Get difficulty level for a task."""
    if task_name in TASKS:
        return TASKS[task_name].difficulty
    return "unknown"
