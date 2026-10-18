package com.gathin.tvhome;
import org.junit.Test;
import static org.junit.Assert.*;

public class WorkspaceTargetTest {
    @Test public void acceptsExistingWebWorkspace() {
        assertTrue(WorkspaceTarget.isWebUrl("https://workspace.example/sessions"));
        assertTrue(WorkspaceTarget.isWebUrl("http://192.168.1.50:8080/"));
    }
    @Test public void rejectsMissingTargetsAndExecutableSchemes() {
        for (String value : new String[]{"", "intent://shell", "javascript:alert(1)",
                "file:///etc/passwd", "https://user:secret@example.com", "https://", null}) {
            assertFalse(WorkspaceTarget.isWebUrl(value));
        }
    }
}
