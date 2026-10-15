/* Dumps the core options the libnx build of Beetle VB reads, with their
 * translations, as JSON on stdout. Built and run on the host by
 * tico_module.py; it includes the core's own option tables so the module
 * never drifts from what the core accepts. Beetle VB still uses the v1
 * option tables (option_defs_us, option_defs_intl), and translates none of
 * tico's languages: those come out empty and tico_module.py supplies them. */
#include <stdio.h>

#include "libretro_core_options.h"

static void put_string(const char *s)
{
   putchar('"');
   for (; s && *s; s++)
   {
      if (*s == '"' || *s == '\\')
         putchar('\\');
      if (*s == '\n')
         fputs("\\n", stdout);
      else
         putchar(*s);
   }
   putchar('"');
}

static void dump(const char *name, const struct retro_core_option_definition *defs, int english, int last)
{
   const struct retro_core_option_definition *def;
   printf("  ");
   put_string(name);
   printf(": [\n");
   for (def = defs; def && def->key; def++)
   {
      const struct retro_core_option_value *value;
      printf("    {\"key\": ");
      put_string(def->key);
      printf(", \"desc\": ");
      put_string(def->desc);
      printf(", \"info\": ");
      put_string(def->info);
      printf(", \"default\": ");
      put_string(def->default_value);
      printf(", \"values\": [");
      for (value = def->values; value->value; value++)
      {
         printf("%s[", value == def->values ? "" : ", ");
         put_string(value->value);
         printf(", ");
         /* an unlabelled choice is named by its value in English; a
          * translation without a label keeps the English one (null) */
         if (value->label)
            put_string(value->label);
         else if (english)
            put_string(value->value);
         else
            fputs("null", stdout);
         printf("]");
      }
      printf("]}%s\n", def[1].key ? "," : "");
   }
   printf("  ]%s\n", last ? "" : ",");
}

int main(void)
{
   /* tico's languages, by their lang/*.json name */
   static const struct { const char *name; int language; } languages[] = {
      {"en", RETRO_LANGUAGE_ENGLISH},
      {"de", RETRO_LANGUAGE_GERMAN},
      {"es", RETRO_LANGUAGE_SPANISH},
      {"fr", RETRO_LANGUAGE_FRENCH},
      {"ja", RETRO_LANGUAGE_JAPANESE},
      {"pt", RETRO_LANGUAGE_PORTUGUESE_BRAZIL},
      {"ru", RETRO_LANGUAGE_RUSSIAN},
      {"zh", RETRO_LANGUAGE_CHINESE_SIMPLIFIED},
   };
   const int count = sizeof(languages) / sizeof(languages[0]);
   int i;
   printf("{\n");
   for (i = 0; i < count; i++)
   {
      const int english = languages[i].language == RETRO_LANGUAGE_ENGLISH;
      dump(languages[i].name,
           english ? option_defs_us : option_defs_intl[languages[i].language],
           english, i == count - 1);
   }
   printf("}\n");
   return 0;
}
