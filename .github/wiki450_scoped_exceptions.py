Import("env")

# Keep the firmware's normal -fno-exceptions profile. Only WikiArchive.cpp needs
# C++ exceptions for the XML article allocation boundary introduced in 4.4.1.
def wiki_archive_exceptions(build_env, node):
    if node.name != "WikiArchive.cpp":
        return node

    ccflags = [flag for flag in build_env.get("CCFLAGS", []) if str(flag) != "-fno-exceptions"]
    cxxflags = [flag for flag in build_env.get("CXXFLAGS", []) if str(flag) != "-fno-exceptions"]
    print("Wiki 4.5.0: enabling C++ exceptions only for WikiArchive.cpp")
    return build_env.Object(
        node,
        CCFLAGS=ccflags + ["-fexceptions"],
        CXXFLAGS=cxxflags + ["-fexceptions"],
    )


env.AddBuildMiddleware(wiki_archive_exceptions)
