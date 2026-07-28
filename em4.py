"""
# em4 project spec
project {
    name = "em4"
    dependencies = [
        "io@stdlib.em4.org",
        "path@stdlib.em4.org",
        "git@libraries.noreply.git-scm.com",
        "s3fs@em4.amazonaws.com"
    ]
    components = {
        main = {
            type = "executable"
            source = "#/main"
        }
    }
    mounts = {
        "/data" = fs(src: "/path/to/data")
        "/repos/workspace" = git(src: "/path/to/repos/workspace", branch: "main")
        "/bucket" = s3(src: "s3://my-bucket", region: "us-east-1")
    }
}

main {
    io.println("Hello, World!")

    # Using '_' instead of '-' for last value evaluation
    path.open("/data") | path.directories.list()
    io.println(_)
    path.open("/repos/workspace") | path.git.status()
    io.println(_)
}
"""
