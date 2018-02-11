#define _POSIX_C_SOURCE 199309L

#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif // __APPLE__

#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <random>
#include <string>

#include <syslog.h>
#include <unistd.h>
#include <tbb/task_scheduler_init.h>

#include "asrel.h"
#include "dovetail_experiments.hpp"
#include "macro.h"

#include "sample_graphs.h"

#define DEFAULT_ADVERSARY "3549"
#define DEFAULT_NUM_MATCHMAKERS 5
#define DEFAULT_NUM_THREADS 1
#define DEFAULT_VERBOSE false
#define DEFAULT_DIAMETER 22
#define DEFAULT_NUM_CONN 100

static const char *usage = "Usage: %s [OPTION]... <asrel_filename> <command>\n\
   options:\n\
      -a=ASN         ASN is used as the adversary.\n\
                     default: 3549\n\
      -d=DIAMETER    Graph DIAMETER limits the depth of Dovetail's DFS.\n\
                     default: 22\n\
      -j=NUM_THREADS Use NUM_THREADS workers when generating samples.\n\
                     default: 1\n\
      -m=NUM_MM      Use NUM_MM matchmaker ASes in samples.\n\
                     default: 5\n\
      -n=NUM_CONN    Simulate up to NUM_CONN repeated connections per trial.\n\
                     default: 100\n\
      -v             Enable verbose logging.\n\n\
<asrel_filename> determines the CAIDA asrel file used in path computation.\n\
<command> is either: frq (for matchmaker frequency analysis)\n\
             or:     conn (for multiple connections security analysis).\n";

struct ProgramArguments {
   const int kNumPositionalArgs = 2;

   // Optional Args
   std::string adversary_asn = DEFAULT_ADVERSARY;
   std::size_t num_matchmakers = DEFAULT_NUM_MATCHMAKERS;
   std::size_t num_threads = DEFAULT_NUM_THREADS;
   bool verbose = DEFAULT_VERBOSE;
   std::size_t graph_diameter = DEFAULT_DIAMETER;
   std::size_t num_conn = DEFAULT_NUM_CONN;

   // Positional Args
   std::string asrel_filename;
   std::string command;
};

static void log_arguments(const ProgramArguments &program_args) {
   syslog(LOG_INFO, "adversary_asn=%s\n", program_args.adversary_asn.c_str());
   syslog(LOG_INFO, "graph_diameter=%zu\n", program_args.graph_diameter);
   syslog(LOG_INFO, "num_threads=%zu\n", program_args.num_threads);
   syslog(LOG_INFO, "num_matchmakers=%zu\n", program_args.num_matchmakers);
   syslog(LOG_INFO, "num_connections=%zu\n", program_args.num_conn);
   syslog(LOG_INFO, "verbose=%s\n", BOOL_TO_STR(program_args.verbose));
   syslog(LOG_INFO, "asrel_filename=%s\n", program_args.asrel_filename.c_str());
   syslog(LOG_INFO, "command=%s\n", program_args.command.c_str());
}

static void
parse_arguments(int argc, char **argv, ProgramArguments *program_args) {
   const char *options = "a:d:j:m:n:v";
   int c = 0;

   while ((c = getopt(argc, argv, options)) != -1) {
      switch (c) {
         case 'a':
            program_args->adversary_asn = std::string(optarg);
            break;
         case 'd':
            program_args->graph_diameter = std::strtoull(optarg, nullptr, 10);
            break;
         case 'j':
            program_args->num_threads = std::strtoull(optarg, nullptr, 10);
            break;
         case 'm':
            program_args->num_matchmakers = std::strtoull(optarg, nullptr, 10);
            break;
         case 'n':
            program_args->num_conn = std::strtoull(optarg, nullptr, 10);
            break;
         case 'v':
            program_args->verbose = true; break;
         case '?':
         default:
            break;
      }
   }

   if (optind + program_args->kNumPositionalArgs != argc) {
      fprintf(stderr, usage, argv[0]);
      syslog(LOG_ERR, "Bad positional arguments.  Exiting...\n");
      std::exit(-1);
   } else {
      program_args->asrel_filename = argv[optind++];
      program_args->command = argv[optind++];
   }
}

static void setup_syslog_mask(const ProgramArguments &program_args) {
   if (program_args.verbose) {
      setlogmask(LOG_UPTO(LOG_INFO));
   } else {
      setlogmask(LOG_UPTO(LOG_NOTICE));
   }
}

int main(int argc, char **argv) {
   openlog(argv[0], LOG_PERROR | LOG_PID, LOG_USER);

   ProgramArguments program_args;
   parse_arguments(argc, argv, &program_args);

   setup_syslog_mask(program_args);
   log_arguments(program_args);

   tbb::task_scheduler_init init(program_args.num_threads);

   std::random_device rd;
   std::mt19937 rng(rd());

   nrl::ASRelIR as_rel_ir;
   nrl::parse_asrel_file(program_args.asrel_filename.c_str(), &as_rel_ir);

   if (program_args.command == "frq") {
      nrl::ASNumber dovetail_asn;
      for (;;) {
         dovetail_asn = nrl::random_dovetail_path_no_tail<nrl::BinaryWDGAdj>
         (
            as_rel_ir,
            program_args.num_matchmakers,
            program_args.graph_diameter,
            rng
         );

         std::cout << dovetail_asn << std::endl;
      } // for

   } else if (program_args.command == "conn") {

      for (int idx = 0; ; ++idx) {
         nrl::multiple_connections_sample_no_tail<nrl::BinaryWDGAdj>
         (
               as_rel_ir,
               program_args.num_matchmakers,
               program_args.num_conn,
               program_args.graph_diameter,
               program_args.adversary_asn,
               idx,
               rng
         );
      } // for

   } else {
      syslog(LOG_ERR, "Bad command.  Exiting...\n");
      std::exit(-1);
   }

   return 0;
}
