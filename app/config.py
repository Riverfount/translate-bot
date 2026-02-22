from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    settings_files=["settings.toml", ".secrets.toml"],
    environments=True,
    env_switcher="ENV_FOR_DYNACONF",
    envvar_prefix="TRANSLATEBOT",
    load_dotenv=True,
    validators=[
        Validator("DOMAIN", must_exist=True),
        Validator("GOOGLE_TRANSLATE_API_KEY", must_exist=True),
        Validator("TARGET_LANGUAGE", must_exist=True),
    ],
)