import fuse
from fuse import Fuse
import blaseball_mike
from blaseball_mike.models import SimulationData
from blaseball_mike.chronicler import get_game_updates, get_games
import stat
import sys

fuse.fuse_python_api = (0, 2)


class Stat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class BlaseFS(Fuse):
    def parse_path(self, path):
        parts = path[1:].split("/")
        path_info = {}
        if parts[0] == "":
            return {"type": "dir"}
        if parts[0] == "by_season":
            path_info["type"] = "dir"
            path_info["sorting"] = "season"
            if len(parts) > 1:
                path_info["season"] = int(parts[1])
            if len(parts) > 2:
                path_info["day"] = int(parts[2])
            if len(parts) > 3:
                path_info["game"] = parts[3]
                path_info["type"] = "file"
        if parts[0] == "by_team":
            path_info["type"] = "dir"
            path_info["sorting"] = "team"
            if len(parts) > 1:
                path_info["team"] = parts[1]
            if len(parts) > 2:
                path_info["season"] = int(parts[2])
            if len(parts) > 3:
                path_info["day"] = int(parts[3].split()[0])
                path_info["type"] = "file"

        return path_info

    def getattr(self, path):
        path_info = self.parse_path(path)
        st = Stat()
        if "type" not in path_info:
            return -fuse.ENOENT
        if path_info["type"] == "dir":
            st.st_mode = stat.S_IFDIR | 0o555
        elif path_info["type"] == "file":
            st.st_mode = stat.S_IFREG | 0o444
            st.st_size = 42069
        return st

    def readdir(self, path, offset):
        dirlist = [".", ".."]

        if path == "/":
            dirlist.extend(["by_season", "by_team"])

        path_info = self.parse_path(path)
        sim_data = SimulationData.load()
        if path_info.get("sorting") == "season":
            if "day" in path_info:
                games = get_games(
                    season=path_info.get("season", 1), day=path_info["day"]
                )
                if not games:
                    return -fuse.ENOENT
                dirlist.extend(
                    f"{game['data']['homeTeamNickname']} vs {game['data']['awayTeamNickname']}"
                    for game in games
                )
            elif "season" in path_info:
                if path_info["season"] > sim_data.season or path_info["season"] < 1:
                    return -fuse.ENOENT
                dirlist.extend(str(day) for day in range(1, 100))
                test_day = 100
                while get_games(season=path_info["season"], count=1, day=test_day):
                    dirlist.append(str(test_day))
                    test_day += 1
            else:
                dirlist.extend(map(str, range(1, sim_data.season + 1)))
        elif path_info.get("sorting") == "team":
            if "season" in path_info:
                games = get_games(
                    season=path_info["season"], team_ids=TEAMS[path_info["team"]]
                )
                if not games:
                    return -fuse.ENOENT
                dirlist.extend(
                    f"{game['data']['day']} vs {home if (home := game['data']['homeTeamNickname']) != path_info['team'] else game['data']['awayTeamNickname']}"
                    for game in games
                )
            elif "team" in path_info:
                if path_info["team"] not in TEAMS:
                    return -fuse.ENOENT
                for season in range(1, sim_data.season + 1):
                    if get_games(
                        season=season, team_ids=TEAMS[path_info["team"]], count=1
                    ):
                        dirlist.append(str(season))
            else:
                dirlist.extend(team for team in TEAMS)

        for dir in dirlist:
            yield fuse.Direntry(dir)

    def read(self, path, size, offset):
        path_info = self.parse_path(path)

        if path_info["type"] != "file":
            return -fuse.ENOENT

        if path_info["sorting"] == "season":
            teams = path_info["game"].replace("\\", "").replace('"', "").split(" vs ")
        elif path_info["sorting"] == "team":
            teams = [path_info["team"]]
        else:
            return -fuse.ENOENT

        games = get_games(
            season=path_info.get("season", 1),
            team_ids=TEAMS[teams[0]],
            day=path_info.get("day", 1),
        )
        if not games:
            return -fuse.ENOENT

        updates = get_game_updates(game_ids=[games[0]["gameId"]], count=2000)

        if not updates:
            return -fuse.ENOENT

        formatted_updates = ""
        for update in updates:
            if formatted_updates:
                formatted_updates += "\n"
            if update["data"]["lastUpdate"]:
                formatted_updates += update["data"]["lastUpdate"] + "\n"
            if update["data"].get("scoreUpdate"):
                formatted_updates += update["data"]["scoreUpdate"] + "\n"
                formatted_updates += f'{update["data"]["homeTeamNickname"]} {update["data"]["homeScore"]}, {update["data"]["awayTeamNickname"]} {update["data"]["awayScore"]}\n'

        slen = len(formatted_updates)

        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            return formatted_updates[offset : offset + size].encode()
        else:
            # Weird bad hack to make tail work...
            end_offset = (
                42069 - offset
            )  # how far from the end of the file it thinks it is
            desired_offset = slen - end_offset
            if desired_offset < slen:
                if end_offset + size > slen:
                    size = slen - offset
                return formatted_updates[
                    slen - end_offset : slen - end_offset + size
                ].encode()


TEAMS = {
    "Mechanics": "46358869-dce9-4a01-bfba-ac24fc56f57e",
    "Worms": "bb4a9de5-c924-4923-a0cb-9d1445f1ee5d",
    "Spies": "9debc64f-74b7-4ae1-a4d6-fce0144b6ea5",
    "Millennials": "36569151-a2fb-43c1-9df7-2df512424c82",
    "Tacos": "878c1bf6-0d21-4659-bfee-916c8314d69c",
    "Moist Talkers": "eb67ae5e-c4bf-46ca-bbbc-425cd34182ff",
    "Crabs": "8d87c468-699a-47a8-b40d-cfb73a5660ad",
    "Sunbeams": "f02aeae2-5e6a-4098-9842-02d2273f25c7",
    "Wild Wings": "57ec08cc-0411-4643-b304-0e80dbc15ac7",
    "Firefighters": "ca3f1c8c-c025-4d8e-8eef-5be6accbeb16",
    "Pies": "23e4cbc1-e9cd-47fa-a35b-bfa06f726cb7",
    "Lovers": "b72f3061-f573-40d7-832a-5ad475bd7909",
    "Fridays": "979aee4a-6d80-4863-bf1c-ee1a78e06024",
    "Georgias": "d9f89a8a-c563-493e-9d64-78e4f9a55d4a",
    "Dale": "b63be8c2-576a-4d6e-8daf-814f8bcea96f",
    "Magic": "7966eb04-efcc-499b-8f03-d13916330531",
    "Lift": "c73b705c-40ad-4633-a6ed-d357ee2e2bcf",
    "Shoe Thieves": "bfd38797-8404-4b38-8b82-341da28b1f83",
    "Garages": "105bc3ff-1320-4e37-8ef0-8d595cb95dd0",
    "Tigers": "747b8e4a-7e50-4638-a973-ea7950a3e739",
    "Flowers": "3f8bbb15-61c0-4e3f-8e4a-907a5fb1565e",
    "Jazz Hands": "a37f9158-7f82-46bc-908c-c9e2dda7c33b",
    "Steaks": "b024e975-1c4a-4575-8936-a3754a08806a",
    "Breath Mints": "adc5b394-8f76-416d-9ce9-813706877b84",
}


if __name__ == "__main__":
    server = BlaseFS()

    server.parser.add_option(
        mountopt="vcr",
        metavar="URL",
        default="",
        help="use blaseball.vcr at URL instead of Chronicler (ie. http://localhost:8000/)",
    )
    server.parse(values=server, errex=1)

    if hasattr(server, "vcr"):
        blaseball_mike.chronicler.v1.BASE_URL = f"{server.vcr}vcr/v1"
        blaseball_mike.chronicler.v2.BASE_URL_V2 = f"{server.vcr}vcr/v2"

        try:
            games = get_games(count=1)
            if not games:
                print(
                    f"Could not connect to blaseball.vcr at {server.vcr}",
                    file=sys.stderr,
                )
                sys.exit(1)
        except:
            print(
                f"Could not connect to blaseball.vcr at {server.vcr}", file=sys.stderr
            )
            sys.exit(1)

    server.main()
