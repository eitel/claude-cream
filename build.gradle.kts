import org.gradle.api.tasks.bundling.Jar
import org.gradle.api.tasks.bundling.Zip

plugins {
    base
}

group = "io.github.eitel"
version = providers.gradleProperty("pluginVersion").get()

val pluginName = providers.gradleProperty("pluginName")

val pluginJar by tasks.registering(Jar::class) {
    archiveBaseName.set(pluginName)
    archiveVersion.set(project.version.toString())
    destinationDirectory.set(layout.buildDirectory.dir("libs"))
    from(layout.projectDirectory.dir("src/main/resources"))
}

val buildPlugin by tasks.registering(Zip::class) {
    dependsOn(pluginJar)
    archiveFileName.set("${pluginName.get()}-${project.version}.zip")
    destinationDirectory.set(layout.buildDirectory.dir("distributions"))
    into("${pluginName.get()}/lib") {
        from(pluginJar.flatMap { it.archiveFile })
    }
}

tasks.assemble {
    dependsOn(buildPlugin)
}
