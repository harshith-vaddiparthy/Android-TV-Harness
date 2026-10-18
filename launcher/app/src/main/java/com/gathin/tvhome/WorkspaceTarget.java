package com.gathin.tvhome;

import java.net.URI;
import java.net.URISyntaxException;

/** Keep workspace launches limited to a web address, without embedded credentials. */
final class WorkspaceTarget {
    static boolean isWebUrl(String value) {
        try {
            URI uri = new URI(value);
            return ("https".equals(uri.getScheme()) || "http".equals(uri.getScheme()))
                    && uri.getHost() != null && uri.getUserInfo() == null;
        } catch (URISyntaxException | NullPointerException e) {
            return false;
        }
    }
}
