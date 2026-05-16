# core/github_ops.py
"""Операции с GitHub API."""
import base64
from github import Github, GithubException
from github import InputGitTreeElement


class GitHubOps:
    def __init__(self, token, repo_name, bot_file_path, logger, notifier=None):
        self.token = token
        self.repo_name = repo_name
        self.bot_file_path = bot_file_path
        self.logger = logger
        self.notifier = notifier

        self.logger.info(f"Подключение к GitHub: {repo_name}")
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.logger.info("GitHub подключён")

    def get_code(self):
        self.logger.info(f"Загрузка {self.bot_file_path}")
        try:
            contents = self.repo.get_contents(self.bot_file_path)
            code = base64.b64decode(contents.content).decode("utf-8")
            self.logger.info(f"Загружено: SHA={contents.sha[:7]}, {len(code)} байт")
            return code, contents.sha
        except GithubException as e:
            if e.status == 404:
                raise FileNotFoundError(f"Файл {self.bot_file_path} не найден")
            raise

    def push(self, new_code, old_sha, commit_message):
        self.logger.info(f"Пуш: {commit_message[:80]}")

        if self.notifier:
            self.notifier.send(f"📤 Коммит: {commit_message[:100]}", "info")

        try:
            blob = self.repo.create_git_blob(new_code, "utf-8")
            ref = self.repo.get_git_ref("heads/main")
            base_commit = self.repo.get_git_commit(ref.object.sha)

            element = InputGitTreeElement(
                path=self.bot_file_path,
                mode='100644',
                type='blob',
                sha=blob.sha
            )

            new_tree = self.repo.create_git_tree([element], base_commit.tree)
            new_commit = self.repo.create_git_commit(
                message=commit_message,
                tree=new_tree,
                parents=[base_commit]
            )

            ref.edit(sha=new_commit.sha)
            self.logger.info(f"Успешно: {new_commit.sha[:7]}")

            if self.notifier:
                self.notifier.send(f"✅ {new_commit.sha[:7]}: {commit_message[:80]}", "success")

            return new_commit.sha

        except GithubException as e:
            if "409" in str(e) or "conflict" in str(e).lower():
                self.logger.warning("Конфликт, повтор...")
                _, new_sha = self.get_code()
                return self.push(new_code, new_sha, commit_message)
            self.logger.error(f"Ошибка пуша: {e}")
            if self.notifier:
                self.notifier.send(f"❌ Ошибка пуша: {str(e)[:200]}", "error")
            raise