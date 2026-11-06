// iSH compatibility additions. CDDL 1.0, see repository LICENSE.md.
namespace MinecraftClient
{
    public static partial class Translations
    {
        private static readonly System.Resources.ResourceManager IshResources =
            new System.Resources.ResourceManager("MinecraftClient.Translations", typeof(Translations).Assembly);
        public static string ish_auth_prompt { get { return IshResources.GetString("ish.auth.prompt"); } }
        public static string ish_auth_failed { get { return IshResources.GetString("ish.auth.failed"); } }
        public static string ish_packet_invalid { get { return IshResources.GetString("ish.protocol.packet_invalid"); } }
        public static string ish_cache_invalid { get { return IshResources.GetString("ish.auth.cache_invalid"); } }
        public static string ish_configuration_finished { get { return IshResources.GetString("ish.protocol.configuration_finished"); } }
        public static string ish_configuration_policy { get { return IshResources.GetString("ish.protocol.configuration_policy"); } }
        public static string ish_chat_not_joined { get { return IshResources.GetString("ish.chat.not_joined"); } }
        public static string ish_chat_secure_required { get { return IshResources.GetString("ish.chat.secure_required"); } }
        public static string ish_chat_length { get { return IshResources.GetString("ish.chat.length"); } }
        public static string ish_console_scope { get { return IshResources.GetString("ish.console.scope"); } }
        public static string ish_console_joined { get { return IshResources.GetString("ish.console.joined"); } }
        public static string ish_console_message { get { return IshResources.GetString("ish.console.message"); } }
        public static string ish_console_player_unverified { get { return IshResources.GetString("ish.console.player_unverified"); } }
        public static string ish_console_error { get { return IshResources.GetString("ish.console.error"); } }
    }
}
