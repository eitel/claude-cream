import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.intellij.ide.ui.UIThemeBean;
import com.intellij.ide.ui.UIThemeBeanKt;
import com.intellij.openapi.editor.colors.impl.EditorColorsSchemeImpl;
import com.intellij.openapi.util.JDOMUtil;
import org.jdom.Element;

import java.nio.file.Path;
import java.nio.file.Files;

/** Loads generated resources with the parser bundled in a local IntelliJ IDEA installation. */
public final class IdeaThemeSmokeTest {
    private IdeaThemeSmokeTest() {}

    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            throw new IllegalArgumentException("Expected two .theme.json files and two scheme XML files");
        }

        for (int index = 0; index < 2; index++) {
            Path path = Path.of(args[index]);
            try (JsonParser parser = new JsonFactory().createParser(Files.readAllBytes(path))) {
                UIThemeBean parsed = UIThemeBeanKt.readTheme(parser, (message, error) -> {
                    throw new IllegalArgumentException(message, error);
                });
                if (parsed.name == null || parsed.ui == null || parsed.ui.isEmpty()) {
                    throw new IllegalArgumentException(path + " did not produce a complete UI theme bean");
                }
                System.out.println("Parsed UI theme: " + parsed.name + " (dark=" + parsed.dark + ")");
            }
        }

        for (int index = 2; index < 4; index++) {
            Path path = Path.of(args[index]);
            EditorColorsSchemeImpl scheme = new EditorColorsSchemeImpl(null);
            Element root = JDOMUtil.load(path);
            scheme.readColors(root.getChild("colors"));
            scheme.readAttributes(root.getChild("attributes"));
            System.out.println("Parsed editor scheme: " + path.getFileName());
        }
    }
}
