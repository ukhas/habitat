/*
    Copyright (C) 2010  Daniel Richman

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    For a full copy of the GNU General Public License,
    see <http://www.gnu.org/licenses/>.
*/

/*
 * cd ~habitat-www
 * mkdir hook
 * chown root:www-data hook
 * chmod 750 hook
 *
 * gcc -D_GNU_SOURCE -Wall -pedantic -O2 runas.temp.c -o hook/runas
 * chown habitat-www:habitat-www hook/runas
 * chmod 755 hook/runas
 * chmod ug+s hook/runas
 *
 * With the above setup, only users in the group www-data will be able to
 * execute the binary, which only root will be able to modify, and it
 * will allow user www-data to become user habitat-www in order to run
 * only one command (controlled, see code below).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <pwd.h>
#include <grp.h>

extern char **environ;

/* User to change to. Binary should be ug+s uname:gname */
#define uid 1013
#define gid 1013
#define uname "habitat-www"
#define gname "habitat-www"

/* The user that's allowed to run the binary */
#define huid 33
#define hgid 33

/* Command & lockfile names */
#define command "/home/habitat-www/update"
#define lockfile "/home/habitat-www/lockfile"

char *argv[] = {command};

#define exit_if(cond)  do { if (cond) { exit(EXIT_FAILURE); } } while (0)

int main(int argc, char *argv[])
{
  int i, j, k, l, m, n, o, p, q, r, s;
  int tty_fd, devnull_fd, update_lock_fd, status;
  uid_t ruid, euid, suid;
  gid_t rgid, egid, sgid;
  pid_t pid, pid2, pid3, pidr;
  struct passwd *ubuf;
  struct group *gbuf;

  /* Check UIDs and GIDs */
  r = getresuid(&ruid, &euid, &suid);
  s = getresgid(&rgid, &egid, &sgid);

  exit_if(r != 0 || s != 0);
  exit_if(euid != uid || suid != uid || egid != gid || sgid != gid);
  exit_if(ruid != huid || rgid != hgid);

  /* Check user & group name */
  gbuf = getgrgid(gid);
  exit_if(gbuf == NULL || strcmp(gbuf->gr_name, uname) != 0);

  ubuf = getpwuid(uid);
  exit_if(ubuf == NULL || strcmp(ubuf->pw_name, gname) != 0);

  /* Set real & effective uid & gid */
  o = setresuid(uid, uid, uid);
  n = setresgid(gid, gid, gid);

  exit_if(o != 0 || n != 0);

  /* CGI Response */
  fprintf(stdout, "Content-Type: text/plain\r\n"
                  "\r\n"
                  "Moo?");
  fflush(stdout);

  /* The process exits after forking and the response will be sent then */
  update_lock_fd = open(lockfile, O_WRONLY|O_CREAT|O_NONBLOCK, 0644);
  exit_if(update_lock_fd == -1);

  /* Assign it to fd 3 */
  p = dup2(update_lock_fd, 3);
  update_lock_fd = 3;
  exit_if(p != 3);

  q = flock(update_lock_fd, LOCK_EX | LOCK_NB);
  /* If we failed to get the lock, just give up */
  exit_if(q != 0);

  /* flocks are automatically released if the file's descriptor closes,
   * for example, upon exit. */

  /* First fork */
  pid = fork();
  exit_if(pid < 0);

  if (pid > 0)
  {
    /* Parent */
    exit(EXIT_SUCCESS);
  }

  /* Start a new process group */
  /* If setsid fails then we are already a process group leader */
  setsid();

  /* Second fork */
  pid2 = fork();
  exit_if(pid2 < 0);

  if (pid2 > 0)
  {
    exit(EXIT_SUCCESS);
  }

  /* From start-stop-daemon.c (dpkg): sever any ties to the parent */
  tty_fd = open("/dev/tty", O_RDWR);
  devnull_fd = open("/dev/null", O_RDWR);

  ioctl(tty_fd, TIOCNOTTY, 0);
  close(tty_fd);

  umask(022);

  k = dup2(devnull_fd, 0);
  l = dup2(devnull_fd, 1);
  m = dup2(devnull_fd, 2);

  exit_if(k == -1 || l == -1 || m == -1);

  /* Keep fds 0, 1, 2, 3 */
  for (i = getdtablesize() - 1; i >= 4; --i)
  {
    close(i);
  }

  j = chdir("/");
  exit_if(j != 0);

  /* Clear the environment */
  clearenv();

  /* Set $HOME and $PATH */
  setenv("HOME", ubuf->pw_dir, 1);
  setenv("PATH", "/usr/local/bin:/usr/bin:/bin", 1);

  /* Fork off the command */
  pid3 = fork();
  exit_if(pid3 < 0);

  if (pid3 == 0)
  {
    close(update_lock_fd);

    /* Child: Do it */
    execve(command, argv, environ);

    /* execve only returns on failure */
    exit(EXIT_FAILURE);
  }
  else
  {
    /* Parent: wait for it to finish */
    for (;;)
    {
      pidr = waitpid(pid3, &status, 0);
      exit_if(pidr < 0);

      if (WIFEXITED(status) || WIFSIGNALED(status))
      {
        break;
      }
    }

    exit(EXIT_SUCCESS);
  }
}
