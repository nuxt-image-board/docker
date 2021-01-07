from itsdangerous import JSONWebSignatureSerializer
from time import time
from hashids import Hashids
import mysql.connector
import requests
import hashlib


def getUserInput(variable_name, default=None):
    user_input = input(f"Input {variable_name} (Default: {default})>>")
    if user_input == "":
        return default
    else:
        return user_input


def showHelpMessage():
    messages = [
        "NuxtImageBoard setup wizard",
        "Usage: python setup.py <operation_name>",
        "",
        "[Supported operations]",
        "maindb:create",
        "    Create tables needed for working",
        "maindb:drop",
        "    Drop all tables created from this wizard",
        "subdb:create",
        "    Create subapi tables needed for working",
        "subdb:drop",
        "    Drop all subapi tables created from this wizard",
        "mainadmin:create",
        "    Create a new admin for main api",
        "mainuser:create",
        "    Create a new user for main api",
        "subadmin:create",
        "    Create a new admin for sub api",
        "subuser:create",
        "    Create a new user for sub api",
        "invite:create",
        "    Create new invite(s)"
    ]
    print("\n".join(messages))


class NuxtImageBoardSetup():
    def __init__(self, api_db_config, toy_db_config, api_config, toymoney_config, headless=False):
        self.main_conn = mysql.connector.connect(**api_db_config)
        self.sub_conn = mysql.connector.connect(**toy_db_config)
        self.main_cursor = self.main_conn.cursor()
        self.sub_cursor = self.sub_conn.cursor()
        self.api_config = api_config
        self.toymoney_config = toymoney_config
        if headless:
            self.createDatabase()
            self.createMainApiUser(self.createSubApiUser())

    def closeDatabase(self):
        self.main_cursor.close()
        self.sub_cursor.close()
        self.main_conn.close()
        self.sub_conn.close()

    def createMainDatabase(self):
        print("Creating main database...")
        with open("init_maindb.sql", "r", encoding="utf8") as f:
            # Note: execute with multi=True returns generator object
            for _ in self.main_cursor.execute(f.read(), multi=True):
                pass
        self.main_conn.commit()
        print("Create main database success!")

    def createSubDatabase(self):
        print("Creating sub database...")
        with open("init_subdb.sql", "r", encoding="utf8") as f:
            # Note: execute with multi=True returns generator object
            for _ in self.sub_cursor.execute(f.read(), multi=True):
                pass
        self.sub_conn.commit()
        print("Create sub database success!")

    def dropMainDatabase(self):
        tables = [
            "data_comment",
            "data_illust",
            "data_invite",
            "data_log",
            "data_mute",
            "data_mylist",
            "data_news",
            "data_notify",
            "data_ranking",
            "data_replace",
            "data_tag",
            "data_upload",
            "data_user",
            "data_view",
            "data_wiki",
            "info_artist",
            "info_mylist",
            "info_tag"
        ]
        for table_name in tables:
            self.main_cursor.execute(f"DROP TABLE {table_name}")
        self.main_conn.commit()

    def dropSubDatabase(self):
        tables = [
            "transactions",
            "user_inventories",
            "users",
            "machines_inventories",
            "machines",
            "airdrops",
            "products"
        ]
        for table_name in tables:
            self.sub_cursor.execute(f"DROP TABLE {table_name}")
        self.sub_conn.commit()

    def dropDatabaseWithWizard(self, is_sub=False):
        print("Are you sure you want to drop the database?")
        print("ALL DATAS WILL BE REMOVED!")
        confirm = getUserInput("y to continue", "n")
        if confirm == "y":
            if not is_sub:
                self.dropMainDatabase()
            else:
                self.dropSubDatabase()
            print("Success")

    def dropMainDatabaseWithWizard(self):
        self.dropDatabaseWithWizard(False)

    def dropSubDatabaseWithWizard(self):
        self.dropDatabaseWithWizard(True)

    def createSubApiAdmin(self, name, password, money=2147483647, id=1):
        serializer = JSONWebSignatureSerializer(
            self.toymoney_config["salt_jwt"]
        )
        password = self.toymoney_config["salt_password"]+password
        password = hashlib.sha256(password.encode("utf8")).hexdigest()
        token = serializer.dumps({
            'id': 1,
            'seq': 1,
            'is_admin': 1
        }).decode('utf-8')
        self.sub_cursor.execute(
            """INSERT INTO users
            (id, name, money, password, authorization_key, authorization_seq, is_admin)
            VALUES (%s, %s, %s, %s, %s, 1, 1)""",
            (id, name, money, password, token)
        )
        self.sub_conn.commit()
        return token

    def createSubApiAdminWithWizard(self):
        print("Creating sub api admin...")
        username = getUserInput("username", "nbadmin")
        password = getUserInput("password", "nbadmin")
        id = int(getUserInput("id", "1"))
        toyapi_key = self.createSubApiAdmin(username, password, id=id)
        print("Create sub api admin success!")
        print(f"Api key: {toyapi_key}")

    def createSubApiUser(self, display_id="nbadmin"):
        toyApiResp = requests.post(
            f"{self.toymoney_config['endpoint']}/users/create",
            json={
                "name": display_id,
                "password": self.toymoney_config['salt_password'] + display_id
            },
            headers={
                "Authorization": "Bearer " + self.toymoney_config['token']
            }
        )
        if toyApiResp.status_code != 200:
            raise Exception("ToyMoneyへのリクエストに失敗しました")
        resp = toyApiResp.json()
        return resp["apiKey"]

    def createSubApiUserWithWizard(self):
        print("Creating sub api user...")
        username = getUserInput("username", "nbadmin")
        toyapi_key = self.createSubApiUser(username)
        print("Create sub api user success!")
        print(f"Api key: {toyapi_key}")

    def generateMainApiKey(self, accountID):
        self.main_cursor.execute(
            "SELECT userApiSeq,userPermission FROM data_user WHERE userID=%s",
            (accountID,)
        )
        apiSeq, apiPermission = self.main_cursor.fetchall()[0]
        serializer = JSONWebSignatureSerializer(
            self.api_config["salt_jwt"]
        )
        token = serializer.dumps({
            'id': accountID,
            'seq': apiSeq + 1,
            'permission': apiPermission
        }).decode('utf-8')
        self.main_cursor.execute(
            """UPDATE data_user SET userApiSeq=userApiSeq+1, userApiKey=%s
            WHERE userID=%s""",
            (token, accountID)
        )
        self.main_conn.commit()
        return token

    def createMainApiUser(
        self,
        toyapi_key,
        display_id="nbadmin",
        username="nbadmin",
        password="nbadmin",
        permission=5
    ):
        # パスワードをハッシュ化
        password = self.api_config["salt_pass"]+password
        password = hashlib.sha256(password.encode("utf8")).hexdigest()
        # ユーザーを追加
        self.main_cursor.execute(
            """INSERT INTO data_user
            (userDisplayID, userName, userPassword,
            userToyApiKey, userPermission)
            VALUES (%s,%s,%s,%s,%s)""",
            (display_id, username, password, toyapi_key, permission)
        )
        # ユーザー内部IDを取得
        self.main_cursor.execute(
            """SELECT userID FROM data_user
            WHERE userDisplayID=%s AND userPassword=%s""",
            (display_id, password)
        )
        user_id = self.main_cursor.fetchall()[0][0]
        api_key = self.generateMainApiKey(user_id)
        # 自分自身の招待を作成(しないとgetSelfAccountで詰まる)
        self.main_cursor.execute(
            """INSERT INTO data_invite
            (inviter, invitee, inviteCode, inviteCreated, inviteUsed)
            VALUES
            (%s, %s, 'SELF', current_timestamp(), current_timestamp())""",
            (user_id, user_id)
        )
        # マイリストの作成
        self.main_cursor.execute(
            """INSERT INTO info_mylist
            (mylistName, mylistDescription, userID)
            VALUES (%s,%s,%s)""",
            (f"{username}のマイリスト", "", user_id)
        )
        self.main_conn.commit()
        return user_id, api_key

    def createMainApiUserWithWizard(self):
        print("Creating main api user...")
        display_id = getUserInput("display id", "nbadmin")
        username = getUserInput("username", "nbadmin")
        password = getUserInput("password", "nbadmin")
        permission = getUserInput("permission", "9")
        toyapi_key = getUserInput("toyapi_key", "auto generate")
        if toyapi_key == "auto generate":
            toyapi_key = cl.createSubApiUser(display_id)
        else:
            self.toymoney_config["token"] = toyapi_key
        user_id, api_key = cl.createMainApiUser(
            toyapi_key,
            display_id, username, password, permission
        )
        print("Create user success!")
        print(f"User id: {user_id}")
        print(f"Api key: {api_key}")

    def createMainApiAdmin(
        self,
        toyapi_key,
        display_id="nbadmin",
        username="nbadmin",
        password="nbadmin",
        permission=9
    ):
        self.createMainApiUser(toyapi_key, display_id, username, password, permission)

    def createMainApiAdminWithWizard(self):
        print("Creating main api admin...")
        display_id = getUserInput("display id", "nbadmin")
        username = getUserInput("username", "nbadmin")
        password = getUserInput("password", "nbadmin")
        toyapi_key = getUserInput("toyapi_key", "auto generate")
        if toyapi_key == "auto generate":
            toyapi_key = cl.createSubApiUser(display_id)
        else:
            self.toymoney_config["token"] = toyapi_key
        user_id, api_key = cl.createMainApiUser(
            toyapi_key,
            display_id, username, password, 9
        )
        print("Create admin success!")
        print(f"User id: {user_id}")
        print(f"Api key: {api_key}")

    def createInvite(self, user_id, invite_code="RANDOM", code_count=1):
        invite_codes = []
        for _ in range(code_count):
            if invite_code == "RANDOM":
                hash_gen = Hashids(
                    salt=self.api_config['salt_invite'],
                    min_length=8
                )
                code = hash_gen.encode(int(time()) + user_id)
            else:
                code = invite_code
            invite_codes.append(code)
            self.main_cursor.execute(
                """INSERT INTO data_invite
                (inviter, inviteCode) VALUES (%s, %s)""",
                (user_id, code)
            )
        self.main_conn.commit()
        return invite_codes

    def createInviteWithWizard(self):
        print("Creating invite...")
        user_id = int(getUserInput("user id", "1"))
        invite_code = getUserInput("invite code", "RANDOM")
        code_count = int(getUserInput("code count", "1"))
        codes = cl.createInvite(
            user_id,
            invite_code,
            code_count
        )
        print("Create invite success!")
        print("Invite codes:")
        print("\n".join(codes))


if __name__ == "__main__":
    # Read commandline params
    import sys
    args = sys.argv
    if len(args) != 2:
        showHelpMessage()
        sys.exit()
    supported_operations = [
        "maindb:create", "maindb:drop",
        "subdb:create", "subdb:drop",
        "mainuser:create", "mainadmin:create",
        "subuser:create", "subadmin:create",
        "invite:create"
    ]
    if args[1] not in supported_operations:
        print("Unsupported operation.\nCheck your syntax.\n")
        showHelpMessage()
        sys.exit()
    # Read environment values
    from os import environ
    from dotenv import load_dotenv
    load_dotenv(verbose=True, override=True)
    api_db_config = {
        'host': environ.get('DB_HOST'),
        'port': environ.get('PORT_API_MARIA'),
        'user': environ.get('DB_USER'),
        'password': environ.get('DB_PASS'),
        'database': environ.get('DB_NAME')
    }
    toy_db_config = {
        'host': environ.get('DB_HOST'),
        'port': environ.get('PORT_TOY_MARIA'),
        'user': environ.get('DB_USER'),
        'password': environ.get('DB_PASS'),
        'database': environ.get('TOYMONEY_DB')
    }
    api_config = {
        'salt_jwt': environ.get('SALT_JWT'),
        'salt_pass': environ.get('SALT_PASS'),
        'salt_invite': environ.get('SALT_INVITE')
    }
    toymoney_config = {
        'endpoint': environ.get('TOYMONEY_ENDPOINT'),
        'token': environ.get('TOYMONEY_TOKEN'),
        'salt_jwt': environ.get('TOYMONEY_SALT'),
        'salt_password': environ.get('TOYMONEY_PASSWORD_HEAD')
    }
    cl = NuxtImageBoardSetup(
        api_db_config,
        toy_db_config,
        api_config,
        toymoney_config
    )
    # Doing selected operation
    supported_operations = {
        "maindb:create": cl.createMainDatabase,
        "maindb:drop": cl.dropMainDatabaseWithWizard,
        "subdb:create": cl.createSubDatabase,
        "subdb:drop": cl.dropSubDatabaseWithWizard,
        "mainuser:create": cl.createMainApiUserWithWizard,
        "mainadmin:create": cl.createMainApiAdminWithWizard,
        "subuser:create": cl.createSubApiUserWithWizard,
        "subadmin:create": cl.createSubApiAdminWithWizard,
        "invite:create": cl.createInviteWithWizard,
    }
    supported_operations[args[1]]()
    cl.closeDatabase()
