import auth
import sys

def main():
    if len(sys.argv) < 2:
        print("usage: ./initrights.py [snowflake]")

    subject = sys.argv[1]

    db = auth.RightsDB("rights.db")
    db.write_permission(auth.SCOPE_USER, subject, auth.declare_right("MANAGE_PERMISSIONS"), 1)

if __name__ == '__main__':
    main()
