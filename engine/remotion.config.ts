import { Config } from '@remotion/cli/config';

/**
 * Base render settings for the Creator Engine.
 *
 * IMPORTANT: concurrency stays at 2. Higher values cause frame drops/errors
 * on Apple Silicon with OffthreadVideo-heavy compositions.
 * Do NOT raise it to 4.
 */
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setConcurrency(2);
