from functools import wraps
from pathlib import Path

import click

from deeppavlov_dreamtools import commands, AssistantDist


class ContextObject:
    def __init__(self, dream_root: Path):
        self.dream_root = dream_root


def must_be_inside_dream(f):
    """
    Check if dreamtools is run from inside the Dream root directory or with the correct -D/--dream option.
    The logic is subject to change.
    """

    @wraps(f)
    def must_be_inside_dream_wrapper(click_context: click.Context, **kwargs):
        dream_root = click_context.obj.dream_root
        dream_subdirs = ["assistant_dists", "annotators", "skills"]

        cwd_subdirs = list(dream_root.glob("*"))
        is_inside_dream = all(dream_root / s in cwd_subdirs for s in dream_subdirs)

        if not is_inside_dream:
            command_name = "dreamtools"
            command = click_context.command_path
            last_name_char = command.rfind(command_name) + len(command_name)
            possible_command = f"{command[:last_name_char]} -D ~/projects/dream {command[last_name_char + 1:]}"
            exception_message = (
                f"{click_context.obj.dream_root.absolute()} is not a Dream directory.\n\n"
                "Make sure you run 'dreamtools' from inside the Dream directory or provide -D/--dream, e.g.:\n"
                f"{possible_command}"
            )
            raise click.exceptions.BadParameter(exception_message, param_hint="-D/--dream")
        return f(click_context, **kwargs)

    return must_be_inside_dream_wrapper


click_path_type = click.Path(
    exists=True,
    file_okay=False,
    dir_okay=True,
    resolve_path=True,
    writable=True,
    path_type=Path,
)


@click.group()
# Here you can provide @click.argument/option to the main command 'dreamtools'
@click.option(
    "-D",
    "--dream",
    envvar="DREAM_ROOT_DIR",
    default=Path("."),
    type=click_path_type,
    help="Dream root directory. Defaults to ./",
)
@click.pass_context
def cli(ctx: click.Context, dream: Path):
    """dreamtools is a command line utility which enhances your DeepPavlov Dream development experience"""
    ctx.obj = ContextObject(dream)


@cli.group()
@click.pass_context
def new(ctx: click.Context):
    """Create new distribution or skill"""


@new.command("dff")
@click.argument("name")
@click.option("-d", "--dist", required=True, help="Dream distribution name")
@click.option("-p", "--port", required=True, help="DFF skill port")
@click.option(
    "--all",
    "all_configs",
    is_flag=True,
    default=False,
    help="Add definition to all docker-compose configs (defaults to False). Overrides all other --compose-* flags",
)
@click.option(
    "--compose-override/--no-compose-override",
    default=False,
    help="Add definition to docker-compose.override.yml (defaults to False)",
)
@click.option(
    "--compose-dev/--no-compose-dev",
    default=False,
    help="Add definition to dev.yml config (defaults to False)",
)
@click.option(
    "--compose-proxy/--no-compose-proxy",
    default=False,
    help="Add definition to proxy.yml config (defaults to False)",
)
@click.option(
    "--compose-local/--no-compose-local",
    default=False,
    help="Add definition to local.yml config (defaults to False)",
)
@click.pass_context
@must_be_inside_dream
def new_dff(
    ctx: click.Context,
    name: str,
    dist: str,
    port: int,
    all_configs: bool,
    compose_override: bool,
    compose_dev: bool,
    compose_proxy: bool,
    compose_local: bool,
):
    """Creates new dff skill in ./skills"""
    if all_configs:
        compose_override = compose_dev = compose_proxy = compose_local = True

    new_dff_path = commands.new.dff(
        name,
        ctx.obj.dream_root,
        dist,
        port,
        compose_override,
        compose_dev,
        compose_proxy,
        compose_local,
    )
    click.echo(
        f"Created new dff skill at {new_dff_path}.\n"
        f"Don't forget to define your state formatter '{name}_formatter' "
        f"in 'dream/state_formatters/dp_formatters.py'"
    )


@new.command("dist")
@click.argument("name")
@click.option("--display-name", help="Human-readable distribution name")
@click.option("--description", help="Distribution description")
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Overwrite distribution directory if it exists",
)
@click.pass_context
@must_be_inside_dream
def new_dist(ctx: click.Context, name: str, display_name: str, description: str, overwrite: bool):
    """Creates new distribution in ./assistant_dists"""

    try:
        dist = AssistantDist.from_name("dream_persona_prompted", ctx.obj.dream_root)
        cloned_dist = dist.clone(name, display_name, description)
        cloned_dist.save(overwrite)

        click.echo(f"Created new Dream distribution {cloned_dist.name}")
    except FileExistsError:
        raise click.ClickException(
            f"{name} distribution already exists! "
            "Run 'dreamtools new dist' with --overwrite flag to avoid this error message"
        )


@new.command("skill")
@click.argument("name")
@click.pass_context
@must_be_inside_dream
def new_skill(ctx: click.Context, name):
    """Create new basic skill template in ./skills"""
    click.echo(f"New skill not implemented yet")


@new.command("local")
@click.option("-d", "--dist", help="Dream distribution name")
@click.option(
    "-s",
    "--services",
    multiple=True,
)
@click.option("--drop-ports/--no-drop-ports", default=True)
@click.option("--single-replica/--no-single-replica", default=True)
@click.pass_context
@must_be_inside_dream
def new_local(
    ctx: click.Context,
    dist: str,
    services: list,
    drop_ports: bool,
    single_replica: bool,
):
    """Create new local.yml"""
    path = commands.new.local_yml(
        dist,
        ctx.obj.dream_root,
        services,
        drop_ports=drop_ports,
        single_replica=single_replica,
    )
    click.echo(f"Created new local.yml under {path}")


@cli.group()
@click.pass_context
def clone(ctx: click.Context):
    """Clone distribution or skill"""


@clone.command("dist")
@click.argument("name")
@click.option("--template", help="Name of the original distribution")
@click.option("--display-name", help="Human-readable distribution name")
@click.option("--description", help="Distribution description")
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Overwrite distribution directory if it exists",
)
@click.pass_context
@must_be_inside_dream
def clone_dist(ctx: click.Context, name: str, template: str, display_name: str, description: str, overwrite: bool):
    """Clones distribution from a template in ./assistant_dists"""

    try:
        dist = AssistantDist.from_name(template, ctx.obj.dream_root)
        cloned_dist = dist.clone(name, display_name, description)
        cloned_dist.save(overwrite)

        click.echo(f"Created new Dream distribution {cloned_dist.name}")
    except FileExistsError:
        raise click.ClickException(
            f"{name} distribution already exists! "
            "Run 'dreamtools new dist' with --overwrite flag to avoid this error message"
        )


@cli.group()
@click.pass_context
def verify(ctx: click.Context):
    """Verify distribution or skill"""


@verify.command("dist")
@click.argument("name")
@click.option("--all", is_flag=True, default=True)
@click.option("--mandatory/--no-mandatory", default=True)
@click.option("--advised/--no-advised", default=True)
@click.option("--optional/--no-optional", default=True)
@click.pass_context
@must_be_inside_dream
def verify_dist(ctx: click.Context, name, **kwargs):
    """Verify distribution"""
    # for response in commands.verify.dist(name, ctx.obj.dream_root):
    #     click.echo(response)


@verify.command("dff")
@click.argument("name")
@click.pass_context
@must_be_inside_dream
def verify_dff(ctx: click.Context, name):
    """Verify dff skill"""
    click.echo(f"Verified dff {name}")


@verify.command("downloads")
@click.argument("name")
@click.pass_context
@must_be_inside_dream
def verify_downloads(ctx: click.Context, name):
    """Verify downloads"""
    click.echo(f"Verified downloads {name}")


@cli.group()
@click.pass_context
def test(ctx: click.Context):
    """Test something"""


@test.command("api")
@click.argument("name")
@click.option("--xlsx", is_flag=True)
def test_api(name, xlsx: bool):
    """Test api"""
    click.echo(f"Tested API {name}, xlsx = {xlsx}")


if __name__ == "__main__":
    cli()
