#define _POSIX_C_SOURCE 199309L

#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif // __APPLE__

#include <cstddef>
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
#define DEFAULT_NUM_THREADS 60
#define DEFAULT_VERBOSE false

struct ProgramArguments {
   const int kNumPositionalArgs = 2;

   // Optional Args
   std::string adversary_asn = DEFAULT_ADVERSARY;
   std::size_t num_matchmakers = DEFAULT_NUM_MATCHMAKERS;
   std::size_t num_threads = DEFAULT_NUM_THREADS;
   bool verbose = DEFAULT_VERBOSE;

   // Positional Args
   std::string asrel_filename;
   std::string command;
};

static void log_arguments(const ProgramArguments &program_args) {
   syslog(LOG_INFO, "adversary_asn=%s\n", program_args.adversary_asn.c_str());
   syslog(LOG_INFO, "num_matchmakers=%zu\n", program_args.num_matchmakers);
   syslog(LOG_INFO, "num_threads=%zu\n", program_args.num_threads);
   syslog(LOG_INFO, "verbose=%s\n", BOOL_TO_STR(program_args.verbose));
   syslog(LOG_INFO, "asrel_filename=%s\n", program_args.asrel_filename.c_str());
   syslog(LOG_INFO, "command=%s\n", program_args.command.c_str());
}

static void
parse_arguments(int argc, char **argv, ProgramArguments *program_args) {
   const char *options = "a:j:m:v";
   int c = 0;

   while ((c = getopt(argc, argv, options)) != -1) {
      switch (c) {
         case 'a':
            program_args->adversary_asn = std::string(optarg);
            break;
         case 'j':
            program_args->num_threads = std::strtoull(optarg, nullptr, 10);
            break;
         case 'm':
            program_args->num_matchmakers = std::strtoull(optarg, nullptr, 10);
            break;
         case 'v':
            program_args->verbose = true; break;
         case '?':
         default:
            break;
      }
   }

   if (optind + program_args->kNumPositionalArgs != argc) {
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
               100,
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
