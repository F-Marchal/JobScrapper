import cloup
import os
HELP = (
        "An email to contact you. This is mandatory to comply with Geopy terms\n"
        "of services. Your contact information will be transmitted to\n"
        "geopy and might be written inside (local) log file / terminal."
    )
CONTACT_OPTION = cloup.option(
    "-c",
    "--contact",
    # required=True,
    type=str,
    default=None,
    help=HELP,
)

def ask_contact(workdir: str, can_load: bool =True):
    contact_file = os.path.abspath(os.path.join(workdir, "contact.txt"))
    if can_load and os.path.exists(contact_file):
        with open(contact_file, "r") as f:
            contact = f.read()
        return contact

    print("Please enter your contact information:", HELP)
    print()
    email = ""
    while not email:
        email = input("Your email : ")
        if not "@" in email or len(email) < 4 or "." not in email.split("@")[1]:
            print(f"`{email}` does not look like a valid email address.\nPlease try again :\n")
            email = ""
            continue

        print(f"Please Confirm that your email is :\n{email}")
        conf = input("Y / N : ")
        if conf.lower() not in ("yes", "y"):
            email = ""
            print()
            continue

        print()
        print("Do you want to save your contact for future runs ?")
        print(f"If 'Y', it will be saved in {contact_file}")
        conf = input("Y / N : ")
        if conf.lower() in ("yes", "y"):
            with open(contact_file, "w") as f:
                f.write(email)
            print("Done.")
        else:
            print("Your email have not been saved.")
        print()
        print()
    return email

@cloup.command()
@cloup.pass_context
def configure_contact(ctx):
    """Runs the contact information configuration tool."""
    print()
    ask_contact(ctx.obj["workdir"], can_load=False)

if __name__ == "__main__":
    print("\n\nRESULT : ", ask_contact("./"))