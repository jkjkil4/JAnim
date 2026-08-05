import click

from janim.locale import set_lang


# 提前解析 --lang 参数
@click.command(
    add_help_option=False,
    context_settings={'ignore_unknown_options': True, 'allow_extra_args': True},
)
@click.option('--lang')
def parse_lang(lang) -> None:
    if lang:
        set_lang(lang)


def main() -> None:
    parse_lang(standalone_mode=False)

    from janim.cli.parse import cli  # 延迟导入，以确保先设置 lang 再展开 i18n

    cli()


if __name__ == '__main__':
    main()
